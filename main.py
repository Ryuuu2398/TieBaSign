# -*- coding:utf-8 -*-
import os
import requests
import hashlib
import time
import copy
import logging
import random

import smtplib
from email.mime.text import MIMEText


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API_URL
LIKIE_URL = "http://c.tieba.baidu.com/c/f/forum/like"
TBS_URL = "http://tieba.baidu.com/dc/common/tbs"
SIGN_URL = "http://c.tieba.baidu.com/c/c/forum/sign"

ENV = os.environ

HEADERS = {
    'Host': 'tieba.baidu.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36',
}
SIGN_DATA = {
    '_client_type': '2',
    '_client_version': '9.7.8.0',
    '_phone_imei': '000000000000000',
    'model': 'MI+5',
    "net_type": "1",
}

# VARIABLE NAME
COOKIE = "Cookie"
BDUSS = "BDUSS"
EQUAL = r'='
EMPTY_STR = r''
TBS = 'tbs'
PAGE_NO = 'page_no'
ONE = '1'
TIMESTAMP = "timestamp"
DATA = 'data'
FID = 'fid'
SIGN_KEY = 'tiebaclient!!!'
UTF8 = "utf-8"
SIGN = "sign"
KW = "kw"
SIGNED = '160002'

s = requests.Session()


def get_tbs(bduss):
    logger.info("获取tbs开始")
    headers = copy.copy(HEADERS)
    headers.update({COOKIE: EMPTY_STR.join([BDUSS, EQUAL, bduss])})
    try:
        tbs = s.get(url=TBS_URL, headers=headers, timeout=5).json()[TBS]
    except Exception as e:
        logger.error("获取tbs出错" + e)
        logger.info("重新获取tbs开始")
        tbs = s.get(url=TBS_URL, headers=headers, timeout=5).json()[TBS]
    logger.info("获取tbs结束")
    return tbs


def get_favorite(bduss):
    logger.info("获取关注的贴吧开始")
    # 客户端关注的贴吧
    returnData = {}
    i = 1
    data = {
        'BDUSS': bduss,
        '_client_type': '2',
        '_client_id': 'wappc_1534235498291_488',
        '_client_version': '9.7.8.0',
        '_phone_imei': '000000000000000',
        'from': '1008621y',
        'page_no': '1',
        'page_size': '200',
        'model': 'MI+5',
        'net_type': '1',
        'timestamp': str(int(time.time())),
        'vcode_tag': '11',
    }
    data = encodeData(data)
    try:
        res = s.post(url=LIKIE_URL, data=data, timeout=5).json()
    except Exception as e:
        logger.error("获取关注的贴吧出错" + e)
        return []
    logger.info("成功获取关注的贴吧第1页")
    returnData = res
    if 'forum_list' not in returnData:
        returnData['forum_list'] = []
    if res['forum_list'] == []:
        logger.error("获取关注的贴吧失败，未发现任何贴吧")
        return {'gconforum': [], 'non-gconforum': []}
    if 'non-gconforum' not in returnData['forum_list']:
        returnData['forum_list']['non-gconforum'] = []
    if 'gconforum' not in returnData['forum_list']:
        returnData['forum_list']['gconforum'] = []
    while 'has_more' in res and res['has_more'] == '1':
        i = i + 1
        data = {
            'BDUSS': bduss,
            '_client_type': '2',
            '_client_id': 'wappc_1534235498291_488',
            '_client_version': '9.7.8.0',
            '_phone_imei': '000000000000000',
            'from': '1008621y',
            'page_no': str(i),
            'page_size': '200',
            'model': 'MI+5',
            'net_type': '1',
            'timestamp': str(int(time.time())),
            'vcode_tag': '11',
        }
        data = encodeData(data)
        try:
            res = s.post(url=LIKIE_URL, data=data, timeout=5).json()
        except Exception as e:
            logger.error("获取关注的贴吧出错" + e)
            continue
        logger.info("成功获取关注的贴吧第{}页".format(i))
        if 'forum_list' not in res:
            continue
        if 'non-gconforum' in res['forum_list']:
            returnData['forum_list']['non-gconforum'].append(res['forum_list']['non-gconforum'])
        if 'gconforum' in res['forum_list']:
            returnData['forum_list']['gconforum'].append(res['forum_list']['gconforum'])

    t = []
    for i in returnData['forum_list']['non-gconforum']:
        if isinstance(i, list):
            for j in i:
                if isinstance(j, list):
                    for k in j:
                        t.append(k)
                else:
                    t.append(j)
        else:
            t.append(i)
    for i in returnData['forum_list']['gconforum']:
        if isinstance(i, list):
            for j in i:
                if isinstance(j, list):
                    for k in j:
                        t.append(k)
                else:
                    t.append(j)
        else:
            t.append(i)
    logger.info("获取关注的贴吧结束")
    return t


def encodeData(data):
    s = EMPTY_STR
    keys = data.keys()
    for i in sorted(keys):
        s += i + EQUAL + str(data[i])
    sign = hashlib.md5((s + SIGN_KEY).encode(UTF8)).hexdigest().upper()
    data.update({SIGN: str(sign)})
    return data


def client_sign(bduss, tbs, fid, kw):
    # 客户端签到
    logger.info("开始签到贴吧：" + kw)
    data = copy.copy(SIGN_DATA)
    data.update({BDUSS: bduss, FID: fid, KW: kw, TBS: tbs, TIMESTAMP: str(int(time.time()))})
    data = encodeData(data)
    try:
        res = s.post(url=SIGN_URL, data=data, timeout=5).json()
    except Exception as e:
        logger.error("签到失败" + e)
    return res

def send_email(signed_list,unsigned_list):
    if ('HOST' not in ENV or 'FROM' not in ENV or 'TO' not in ENV or 'AUTH' not in ENV):
        logger.error("未配置邮箱")
        return
    HOST = ENV['HOST']
    # FROM = 'tieba_sign <{}>'.format(ENV['FROM'])
    FROM = ENV['FROM']
    TO = ENV['TO'].split('#')
    AUTH = ENV['AUTH']
    
    signed_length = len(signed_list)
    unsigned_length = len(unsigned_list)
    subject = f"{time.strftime('%Y-%m-%d', time.localtime())} {signed_length+unsigned_length}个贴吧，成功签到{signed_length}个"
    body = """
    <style>
    .child {
      background-color: rgba(173, 216, 230, 0.19);
      padding: 10px;
    }

    .child * {
      margin: 5px;
    }
    </style>
    """
    body += f"""
        <div class="child">
            <div class="name"> 签到成功:</div>
        """
    for i in signed_list:
        body += f"""
            <div class="name">  { i['name'] }</div>
        """
    body += f"""
        </div>
        <hr>
        <div class="child">
            <div class="name"> 签到失败:</div>
        """
    for i in unsigned_list:
        body += f"""
            <div class="name">  { i['name'] }</div>
        """
    body += f"""
        </div>
        <hr>
        """
    msg = MIMEText(body, 'html', 'utf-8')
    msg['subject'] = subject
    
    try:
        # 建立 SMTP 、SSL 的连接，连接发送方的邮箱服务器
        smtp = smtplib.SMTP_SSL(HOST,465)

        # 登录发送方的邮箱账号
        smtp.login(FROM, AUTH)

         # 发送邮件 发送方，接收方，发送的内容
        smtp.sendmail(FROM, TO, msg.as_string())

        logger.info('邮件发送成功')
 
        smtp.quit()
    except Exception as e:
        logger.error('发送邮件失败' + str(e))

def main():
    if ('BDUSS' not in ENV):
        logger.error("未配置BDUSS")
        return
    b = ENV['BDUSS'].split('#')
    for n, i in enumerate(b):
        logger.info("开始签到第" + str(n) + "个用户")
        tbs = get_tbs(i)
        favorites = get_favorite(i)
        send_email(favorites,favorites)
        return
        follow = copy.copy(favorites)
        success=[]
        for t in range(5):
            failed=[]
            for j in follow:
                time.sleep(random.randint(1,5))
                res = client_sign(i, tbs, j["id"], j["name"])
                if(res['error_code'] == '0'):
                    success.append(j)
                    logger.info('签到成功')
                elif(res['error_code'] == SIGNED):
                    success.append(j)
                    logger.info(res['error_code']+':'+res['error_msg'])
                else:
                    failed.append(j)
                    logger.info(res['error_code']+':'+res['error_msg'])
            if(failed == []):
                break
            follow = copy.copy(failed)
            time.sleep(random.randint(300,600))
            tbs = get_tbs(i)
        logger.info("完成第" + str(n) + "个用户签到")
        send_email(success,failed)
    logger.info("所有用户签到结束")



if __name__ == '__main__':
    main()
