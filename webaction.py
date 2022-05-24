import grequests
import browser_cookie3
import requests
import webbrowser
import time
import json
import os
from tqdm import tqdm


# bypass system proxy
proxies = {
    'https': None,
    'http': None
}

# cookie from chrome
cookies = browser_cookie3.chrome(domain_name='115.com',
                                 cookie_file=os.environ['USERPROFILE']+'\\AppData\Local\\Google\\Chrome\\User Data\\Default\\Network\\Cookies')

# default headers
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36'
}

# register chrome in webbrowser
webbrowser.register('chrome', None,
                    webbrowser.BackgroundBrowser("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"))
chrome = webbrowser.get('chrome')



def get_no_proxy(url):
    return requests.get(url, proxies=proxies, headers=headers, cookies=cookies)


def post_no_proxy(url, data):
    return requests.post(url, proxies=proxies, data=data, headers=headers, cookies=cookies)


def list_folder115(cid, show_folder=True):
    '''
    return the response(json str) of requests
    '''
    # 115的api最大为1200
    if show_folder:
        url = 'https://aps.115.com/natsort/files.php?cid={}&show_dir=1&limit=1200'
    else:
        url = 'https://aps.115.com/natsort/files.php?cid={}&limit=1200'
    return get_no_proxy(url.format(cid))


def glist_folder115(cid_list, show_folder=True, max_retry=5, show_tqdm=True):
    '''
    use grequests to list multiple folders
    return [response(json str)]
    '''
    if not isinstance(cid_list, list):
        raise TypeError('expected list')
    max_size = 200
    if show_folder:
        url = 'https://aps.115.com/natsort/files.php?cid={}&show_dir=1&limit=1200'
    else:
        url = 'https://aps.115.com/natsort/files.php?cid={}&limit=1200'
    if len(cid_list) > max_size:
        cid_list_list = [cid_list[i*max_size:(i+1)*max_size] for i in range(len(cid_list)//max_size)] + [cid_list[-(len(cid_list)%max_size):]]
    else:
        cid_list_list = [cid_list]
    res_fin = []
    for cid_list in tqdm((cid_list_list), desc='115 list gevent@'+str(max_size)) if show_tqdm else cid_list_list:
        req =  [grequests.get(url.format(cid),proxies=proxies, headers=headers, cookies=cookies) for cid in cid_list]
        res = grequests.map(req, size=max_size)
        while None in res and max_retry:
            print('sleep 0.5s')
            time.sleep(1)
            re_index = [i for i in range(len(res)) if not res[i]]
            re_req = [req[i] for i in re_index]
            re_res = grequests.map(re_req, size=max_size)
            for i in range(len(re_index)):
                res[re_index[i]] = re_res[i]
        if not max_retry:
            raise UserWarning('list gevent fail')
        max_retry = 5
        res_fin += res
    return res_fin


def file_info115(fid):
    '''
    return a dict with form:
    {
        'count':str,
        'size':str,
        'file_name':str,
        'paths':[{'file_id':str,'file_name':str}]
    }
    '''
    url = 'https://webapi.115.com/category/get?aid=1&cid={}'
    return json.loads(get_no_proxy(url=url.format(fid)).text)


def rename_multi115(fid_list, name_list, max_try=5, show_tqdm=1):
    '''
    use grequests to rename files in 115
    '''
    for i in range(len(name_list)):
        if len(name_list[i])>255:
            name_list[i] = name_list[i][:255]
    if not isinstance(fid_list, list):
        raise TypeError('expected list')
    if not isinstance(name_list, list):
        raise TypeError('expected list')
    max_size = 50
    url = 'https://webapi.115.com/files/batch_rename'
    if len(name_list) > max_size:
        fid_list_list = [fid_list[i*max_size:(i+1)*max_size] for i in range(len(fid_list)//max_size)] + [fid_list[-(len(fid_list)%max_size):]]
        name_list_list = [name_list[i*max_size:(i+1)*max_size] for i in range(len(name_list)//max_size)] + [name_list[-(len(name_list)%max_size):]]
    else:
        fid_list_list = [fid_list]
        name_list_list = [name_list]
    for fid_list, name_list in tqdm(list(zip(fid_list_list,name_list_list)), desc='115 rename') if show_tqdm else list(zip(fid_list_list,name_list_list)):
        name_list = [
            i.replace('\\', '＼').replace('/', '丨').replace(':', '：').replace('?', '？').replace('"', '＂').replace(
                '<', '＜').replace('>', '＞').replace('|', '丨').replace('*', '＊') for i in name_list]
        data = {'files_new_name['+fid_list[i]+']': name_list[i] for i in range(len(fid_list))}
        res = post_no_proxy(url, data)
        try: 
            json.loads(res.text)['state']
        except json.decoder.JSONDecodeError:
            if max_try:
                time.sleep(2)
                rename_multi115(fid_list, name_list, max_try=max_try-1, show_tqdm=0)
                continue
            else:
                raise Exception('115 rename failed')
        if not json.loads(res.text)['state']:
            if max_try:
                # sleep before retry
                time.sleep(2)
                rename_multi115(fid_list, name_list, max_try=max_try-1, show_tqdm=0)
            else:
                raise Exception('115 rename failed')
        time.sleep(1)


def delete_multi115(fid_list, pid, max_try=5, show_tqdm=1):
    '''
    delete multiple files of ONE folder folder
    '''
    if not isinstance(fid_list, list):
        raise TypeError('expected list')
    if not isinstance(pid, str):
        raise TypeError('expected str')
    max_size = 50
    url = 'https://webapi.115.com/rb/delete'
    if len(fid_list) > max_size:
        fid_list_list = [fid_list[i*max_size:(i+1)*max_size] for i in range(len(fid_list)//max_size)] + [fid_list[-(len(fid_list)%max_size):]]
    else:
        fid_list_list = [fid_list]
    for fid_list in tqdm((fid_list_list), desc='115 delete') if show_tqdm else fid_list_list:
        data = {'fid[{}]'.format(i): fid_list[i] for i in range(len(fid_list))}
        data['pid'] = pid
        data['ignore_warn'] = 1
        res = post_no_proxy(url,data)
        if not json.loads(res.text)['state']:
            if max_try:
                max_try -= 1
                time.sleep(1)
                delete_multi115(fid_list, pid, max_try=max_try, show_tqdm=0)
            else:
                raise Exception('115 delete failed')
        time.sleep(2)


def create_folder115(pid, name, max_try=5):
    '''
    create a folder with name in certain folder
    '''
    if not isinstance(pid,str):
        if isinstance(pid,int):
            pid = str(pid)
        else:
            raise TypeError('expected str or int')
    if not isinstance(name,str):
        raise TypeError('expected str')
    url = 'https://webapi.115.com/files/add'
    data = {'pid':pid, 'cname':name}
    res = post_no_proxy(url,data)
    if not json.loads(res.text)['state']:
        if max_try:
            max_try -= 1
            time.sleep(1)
            create_folder115(pid, name, max_try=max_try)
        else:
            raise Exception('115 create folder failed')


def copy_multi115(fid_list, pid, max_try=5, show_tqdm=1):
    '''
    copy multiple files into ONE folder
    '''
    if not isinstance(fid_list, list):
        raise TypeError('expected list')
    max_size = 50
    url = 'https://webapi.115.com/files/copy'
        
    if len(fid_list) > max_size:
        fid_list_list = [fid_list[i*max_size:(i+1)*max_size] for i in range(len(fid_list)//max_size)] + [fid_list[-(len(fid_list)%max_size):]]
    else:
        fid_list_list = [fid_list]
    for fid_list in tqdm((fid_list_list), desc='115 copy') if show_tqdm else fid_list_list:
        data = {'fid[{}]'.format(index): fid_list[index] for index in range(len(fid_list))}
        data['pid'] = pid
        res = post_no_proxy(url,data)
        if not json.loads(res.text)['state']:
            if max_try:
                max_try -= 1
                time.sleep(1)
                delete_multi115(fid_list, pid, max_try=max_try, show_tqdm=0)
            else:
                raise Exception('115 copy failed')
        time.sleep(2)


def open115(cid_list:list[str]):
    '''
    open multiple folders in webbrowser
    '''
    url = 'https://115.com/?cid={}&offset=0&mode=wangpan'
    if isinstance(cid_list,str):
        cid_list =[cid_list]
    for cid in cid_list:
        chrome.open(url.format(cid))
    

def get_m3u8_by_pc(pc):
    '''
    get m3u8 from pickcode('pc' in response of list_folder115)
    '''
    if not isinstance(pc, str):
        raise TypeError('expected str')
    url = 'https://115.com/api/video/m3u8/{}.m3u8'
    res = get_no_proxy(url.format(pc))
    return res