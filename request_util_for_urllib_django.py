from django.http.multipartparser import MultiPartParser
from django.core.handlers.wsgi import WSGIRequest
from django.core.files.base import ContentFile
from django.http import QueryDict
from enum import Enum
import json
from urllib import request
from urllib import parse
from urllib.error import HTTPError
import io
import mimetypes
import uuid
from django.core.files.uploadedfile import File
from collections import namedtuple

class BaseRequest():

    class SimpleMethod(Enum):
        GET = "GET"
        DELETE = "DELETE"

    class NonSimpleMethod(Enum):
        POST = "POST"
        PUT = "PUT"
        PATCH = "PATCH"

    class ContentType(Enum):
        TEXTPLAIN = "text/plain"
        JSON = "application/json"
        URLENCODED = "application/x-www-form-urlencoded"
        MULTIPART = "multipart/form-data"

        JPEG = "image/jpeg"
        PNG = "image/png"
        PDF = "application/pdf"

        @classmethod
        def get_filename_extension(cls, content_type):
            filename_extension = ""
            if content_type == cls.JPEG.value:
                filename_extension = ".jpeg"
            elif content_type == cls.PNG.value:
                filename_extension = ".png"
            elif content_type == cls.PDF.value:
                filename_extension = ".pdf"

            return filename_extension

class URLLibUtils(BaseRequest):

    def __init__(self, url, http_method=BaseRequest.SimpleMethod.GET, parameters={}, headers={}, content_type=BaseRequest.ContentType.TEXTPLAIN):
        self.url = url
        self.http_method = http_method
        self.parameters = parameters
        self.headers = headers
        self.content_type = content_type

    def urlopen(self):

        if isinstance(self.http_method, BaseRequest.SimpleMethod) and (self.parameters != {}):
            self.parameters = "?" + parse.urlencode(self.parameters) + "/"
            self.url += self.parameters

        req = request.Request(self.url, headers=self.headers, method=self.http_method.value)
        content_type = self.content_type.value

        data = None

        if isinstance(self.http_method, BaseRequest.NonSimpleMethod):
            if content_type == BaseRequest.ContentType.JSON.value:
                data = json.dumps(self.parameters).encode('utf-8')
            elif content_type == BaseRequest.ContentType.URLENCODED.value:
                data = bytes(parse.urlencode(self.parameters), encoding='utf8')
            elif content_type == BaseRequest.ContentType.MULTIPART.value:
                data, content_type = self._get_multipart_form(self.parameters)
            # elif content_type == BaseRequest.ContentType.TEXTPLAIN.value:
            #     print(BaseRequest.ContentType.TEXTPLAIN.value)

            req.data = data
        req.add_header('Content-type', content_type)
        result = self._validate_response(req)
        return result

    def _validate_response(self, req):
        Result = namedtuple('Result', 'is_success response')

        try:
            response = request.urlopen(req, timeout=60)
            status_code = response.getcode()
            if status_code not in range(200, 300):
                raise HTTPError('status code not equal to 2xx')
            json_string = response.read().decode('utf-8')
            dict_from_json = json.loads(json_string)
            result = Result(is_success=True, response=dict_from_json)
        except HTTPError as e:
            print(e.code)
            print(e.reason)
            result = Result(is_success=False, response=e)
        except Exception as e:
            result = Result(is_success=False, response=e)
        finally:
            return result

    def _seperate_files_and_pure_parameters(self, parameters):
        form_fields, files = [], []
        for key, value in parameters.items():
            if isinstance(value, io.BufferedReader) or isinstance(value, File):
                body = value.read()
                mimetype = (
                        mimetypes.guess_type(value.name)[0] or
                        'application/octet-stream'
                )
                files.append((key, value.name, mimetype, body))
            else:
                form_fields.append((key, value))
        return form_fields, files

    def _get_multipart_form(self, parameters):

        form_fields, files = self._seperate_files_and_pure_parameters(parameters)
        boundary = uuid.uuid4().hex.encode('utf-8')
        content_type = BaseRequest.ContentType.MULTIPART.value + '; boundary={}'.format(boundary.decode('utf-8'))

        buffer = io.BytesIO()
        boundary = b'--' + boundary + b'\r\n'

        for name, value in form_fields:
            buffer.write(boundary)
            buffer.write(('Content-Disposition: form-data; '
                'name="{}"\r\n').format(name).encode('utf-8'))
            buffer.write(b'\r\n')
            buffer.write(value.encode('utf-8'))
            buffer.write(b'\r\n')

        for f_name, filename, f_content_type, body in files:
            buffer.write(boundary)
            buffer.write(('Content-Disposition: file; '
                'name="{}"; filename="{}"\r\n').format(
                f_name, filename).encode('utf-8'))
            buffer.write('Content-Type: {}\r\n'.format(f_content_type).encode('utf-8'))
            buffer.write(b'\r\n')
            buffer.write(body)
            buffer.write(b'\r\n')

        buffer.write(b'--' + boundary + b'--\r\n')
        return buffer.getvalue(), content_type

class WSGIRequestUtils(WSGIRequest, BaseRequest):

    def __init__(self, request):
        super().__init__(request.environ)
        self._request = request
        self.headers = {header_key:header_value for header_key, header_value in self._request.META.items() if "HTTP_" in header_key}
        self.url_parameters = self._request.GET.dict()
        self.body_parameters = {}
        self.body_files = {}
        if self._request.method == BaseRequest.NonSimpleMethod.POST.value or self._request.method == BaseRequest.NonSimpleMethod.PUT.value:
            if self._request.content_type == BaseRequest.ContentType.MULTIPART.value:
                parameters, files = MultiPartParser(self._request.META, self._request, self._request.upload_handlers).parse()
                self.body_parameters = {key: value.replace("\r\n--", "") for key, value in parameters.items()}
                self.body_files = files.dict()
                popable_items = []
                for file_name, file in self.body_files.items():
                    if file.content_type == BaseRequest.ContentType.JSON.value:
                        file_content = file.read().decode("utf-8")
                        dict_from_content = json.loads(file_content)
                        self.body_parameters[file_name] = dict_from_content
                        popable_items.append(file_name)
                for item in popable_items: del self.body_files[item]

            elif self._request.content_type == BaseRequest.ContentType.TEXTPLAIN.value:
                file = ContentFile(request.body)
                self.body_files = {"empty": file}
            elif self._request.content_type == BaseRequest.ContentType.URLENCODED.value:
                self.body_parameters = QueryDict(request.body).dict()
            elif self._request.content_type == BaseRequest.ContentType.JSON.value:
                self.body_parameters = json.loads(request.body)
