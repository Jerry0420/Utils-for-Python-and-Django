# Utils for Python and Django
在 Python 及 Django 中的一些實用小工具

## 發送網路請求
### 使用方式

```python
utils = URLLibUtils(url=url, http_method=URLLibUtils.SimpleMethod.GET, parameters={}, headers={}, content_type=URLLibUtils.ContentType.TEXTPLAIN)
result = utils.urlopen()

# result 的型別，是一個 namedtuple
# status_code 為 http status code
# response 為轉成 dict 格式的 http response
result # Result(status_code=status_code, response=response)

# parameters 放入 dict，key 放入相對應的參數名稱，value 可放入任何型別，包括照片、pdf 檔案...等
# 夾帶檔案時 parameter 的寫法
picture_file = open(Path(__file__).absolute().parent / 'meta' / 'xxxxx.jpg', 'rb') 
parameter = {"image_key": picture_file}

# 若要夾帶 query string 在 url 上，將 key-value 以 dict 方式放在 parameters 欄位
# header 為 dict 格式
```

### 優勢
1. 只要兩行程式碼，即可方送網路請求，得到 http response(dict 格式) , http status code
2. 所有的 http method, content type 皆以 namedtuple 方式呼叫，避免輸入字串，增加打錯字風險，以及加快開發速度。

## 在 Django 中處理網路請求
###使用方式

```python
# 在任何 middleware 中或程式碼中放入
# 將 django 原生的 request 轉型成 WSGIRequestUtils 的 object
request = WSGIRequestUtils(request) 

# 在程式中以 dict 格式取得所有 headers
request.headers

# 在程式中以 dict 格式取得所有 query string
request.url_parameters

# 在程式中以 dict 格式取得所有 body 內的參數
request.body_parameters

# 在程式中以 dict 格式取得所有 body 內的檔案
request.body_files
```

### 優勢
1. 將所有 request 內的資訊集中管理，透過單一介面呼叫，加快開發速度
2. 不需記憶 WSGIRequest 內的函數呼叫方式
3. 所有的 http method, content type 皆以 namedtuple 方式呼叫，避免輸入字串，增加打錯字風險，以及加快開發速度。