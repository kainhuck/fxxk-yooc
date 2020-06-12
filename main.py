import os
import re
import time
import json
import requests
import configparser

from html.parser import HTMLParser

BASE_DIR = os.path.dirname(__file__)
ANSDB_DIR = os.path.join(BASE_DIR, "ansDB")
CONFIG_DIR = os.path.join(BASE_DIR, "yooc.ini")

USER_INFO = {}
EXAM_INFO = {}
APP_INFO = {}

QUESTION_COUNT = 0

answerFile = ""

class QuestionPage(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.question_id_array = []

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            for (variable, value) in attrs:
                if variable == "id":
                    if "question-" in value:
                        self.question_id_array.append(value[-8:])


class AnswerOpinions(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.want_next_data = False
        self.opinions_array = []

    def handle_starttag(self, tag, attrs):
        if tag == "p":
            self.want_next_data = True

    def handle_data(self, data):
        if self.want_next_data:
            self.want_next_data = False
            if "正确答案：" in data:
                opinions = data[5:].split("、")
                self.opinions_array.append(opinions)


class AnswerID(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.want_next_data = False
        self.question_value = ""
        self.question_name = ""
        self.opinions_array = []
        self.count = 0
        self.answer_id_array = []
        self.answers_array = []
        self.has_found_correct_answer = False

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            for (variable, value) in attrs:
                if variable == "data-question-value":
                    self.want_next_data = True
                    self.question_value = value
                elif variable == "data-question-name":
                    self.want_next_data = True
                    self.question_name = value[0:8]

    def handle_data(self, data):
        if self.want_next_data:
            self.want_next_data = False
            if self.count >= 100:
                return
            if data[0] == "A":
                self.has_found_correct_answer = False
            if data[0] in self.opinions_array[self.count]:
                if self.has_found_correct_answer:
                    return
                self.answer_id_array.append(self.question_value)
            if len(self.answer_id_array) == len(self.opinions_array[self.count]):
                self.answers_array.append(self.answer_id_array)
                self.answer_id_array = []
                self.count += 1
                self.has_found_correct_answer = True

def ExistAnswerFile():
    answerFile = os.path.join(ANSDB_DIR, f"{EXAM_INFO['groupid']}_{EXAM_INFO['examid']}.txt")

    if not os.path.exists(answerFile):
        with open(answerFile, "w+") as f:
            f.write("{}")

def ExistAnsDB():
    if not os.path.exists(ANSDB_DIR):
        os.mkdir(ANSDB_DIR)
        print("ansDB目录不存在,已为你自动生成")

def mkini():
    with open(CONFIG_DIR, "w+") as f:
        f.writelines([
            "[userinfo]\n",
            "email    = 这里替换成你的账号(邮箱或手机号)\n",
            "password = 这里替换成你的密码\n",
            "\n",
            "[exam]\n",
            "groupID = 这里替换成你的课群ID\n",
            "examID  = 这里替换成你的考试ID\n",
            "\n",
            "[app]\n",
            "circleTimes = 1\n"
        ])

def ParseIni():
    conf = configparser.ConfigParser()
    conf.read(CONFIG_DIR, encoding="utf-8")

    user_info = conf.items('userinfo')
    exam_info = conf.items('exam')
    app_info = conf.items('app')

    assert user_info[0][0] == "email"
    assert user_info[1][0] == "password"
    assert exam_info[0][0] == "groupid"
    assert exam_info[1][0] == "examid"
    assert app_info[0][0] == "circletimes"

    for item in user_info:
        USER_INFO[item[0]] = item[1]

    for item in exam_info:
        EXAM_INFO[item[0]] = item[1]

    for item in app_info:
        APP_INFO[item[0]] = int(item[1])

def ReadFileInfo():
    try:
        ParseIni()
    except Exception as e:
        print(e)
        print("yooc.ini文件不存在或有误,已为你重新生成,请手动修改下面这个文件")
        print(CONFIG_DIR)
        mkini()
        exit()

def InputInfo():
    email = input("请输入账号: ").strip()
    password = input("请输入密码: ").strip()
    groupID = input("请输入课群ID: ").strip()
    examID = input("请输入考试ID: ").strip()
    while True:
        try:
            circleTimes = int(input("请输入答题次数: ").strip())
            if circleTimes < 1:
                print("答题次数应当为大于1")
                continue
            break
        except:
            print("答题次数应当为整数!")

    USER_INFO["email"] = email
    USER_INFO["password"] = password
    EXAM_INFO["groupid"] = groupID
    EXAM_INFO["examid"] = examID
    APP_INFO["circletimes"] = circleTimes

def GetCookies():
    login_url = "https://www.yooc.me/login"
    response = requests.get(login_url)
    return_cookie = {}
    for key, value in response.cookies.items():
        return_cookie[key] = value
    return return_cookie


def Login(cookies):
    form_data = form_data = {"email": USER_INFO["email"], "password":  USER_INFO["password"], "remember": True}
    login_url = "https://www.yooc.me/yiban_account/login_ajax"
    request_headers = {"X-CSRFToken": cookies["csrftoken"]}
    response = requests.post(login_url, data=form_data,
                             headers=request_headers, cookies=cookies)
    return_cookie = {}
    for key, value in response.cookies.items():
        return_cookie[key] = value
    return return_cookie


def RepeatExam(cookies):
    exam_url = f"https://www.yooc.me/group/{EXAM_INFO['groupid']}/exams"
    text = requests.get(exam_url, cookies=cookies).text
    # print(text)
    repeat_url = re.compile("repeat-url=\"(.*?)\"").findall(text)[0]
    request_headers = {"X-CSRFToken": cookies["csrftoken"], "Cookie": "csrftoken=" +
                       cookies["csrftoken"] + "; sessionid=" + cookies["sessionid"]}
    form_data = {"csrfmiddlewaretoken": cookies["csrftoken"]}
    response = requests.post(
        repeat_url, headers=request_headers, data=form_data, cookies=cookies)


def SubmitAnswer(cookies, answers):
    submit_url = f"https://www.yooc.me/group/{EXAM_INFO['groupid']}/exam/{EXAM_INFO['examid']}/answer/submit"
    request_headers = {"X-CSRFToken": cookies["csrftoken"], "Cookie": "csrftoken=" +
                       cookies["csrftoken"] + "; sessionid=" + cookies["sessionid"]}
    form_data = {"csrfmiddlewaretoken": cookies["csrftoken"], "answers": json.dumps(
        answers), "completed": "1", "auto": "0"}
    response = requests.post(
        submit_url, headers=request_headers, data=form_data, cookies=cookies)


def GetExamPage(cookies):
    exam_url = f"https://www.yooc.me/group/{EXAM_INFO['groupid']}/exam/{EXAM_INFO['examid']}/detail"
    return requests.get(exam_url, cookies=cookies).text


def ParseQuestion(page):
    parser = QuestionPage()
    parser.feed(page)
    return parser.question_id_array


def BuildAnswer(question_id_array):
    answerFile = os.path.join(ANSDB_DIR, f"{EXAM_INFO['groupid']}_{EXAM_INFO['examid']}.txt")
    with open(answerFile, 'r') as answer_file:
        answer = json.loads(answer_file.read())
        answers = []
        for question_id in question_id_array:
            answer_chunk = {}
            answer_chunk[question_id] = {}
            answer_chunk[question_id]["1"] = answer.get(question_id, [0])
            answers.append(answer_chunk)
    return answers


def ParseAnswer(page):
    parse = AnswerOpinions()
    parse.feed(page)
    opinions_array = parse.opinions_array
    parse = AnswerID()
    parse.opinions_array = opinions_array
    parse.feed(page)
    return parse.answers_array


def BuildAnswerFile(page):
    answerFile = os.path.join(ANSDB_DIR, f"{EXAM_INFO['groupid']}_{EXAM_INFO['examid']}.txt")
    with open(answerFile, 'r+') as answer_file:
        question_id_array = ParseQuestion(page)
        answers_array = ParseAnswer(page)
        answer = json.loads(answer_file.read())
        for i in range(0, 99):
            answer[question_id_array[i]] = answers_array[i]
        print("当前题库答案数: " + str(len(answer)))
        answer_file.seek(0)
        answer_file.write(json.dumps(answer))
        if(len(answer) == QUESTION_COUNT):
            print("答案已收集完毕，程序退出。")
            exit()


def start():
    ExistAnsDB()

    loginWay = {
        "1": ReadFileInfo,
        "2": InputInfo
    }

    while True:
        print("** 请选择登录方式 **")
        print("1. 从文件读取")
        print("2. 手动输入")
        choose = input(">>> ").strip()
        way = loginWay.get(choose, 0)
        if(way == 0):
            print("输入有误! \n")
        else:
            way()
            break
    
    ExistAnswerFile()

    for i in range(APP_INFO["circletimes"]):
        print(f"开始第{i+1}次答题")
        cookies = Login(GetCookies())
        RepeatExam(cookies)
        print("登录成功")

        page = GetExamPage(cookies)
        print("获取题目成功")
        question_id_array = ParseQuestion(page)
        answers = BuildAnswer(question_id_array)
        SubmitAnswer(cookies, answers)
        print("答题结束")

        print("开始更新题库")
        page = GetExamPage(cookies)
        BuildAnswerFile(page)
        print("题库更新完毕")
        print("程序结束")


def PrintLogo():
    print("\033[36m")
    print(r'''
 ____                 __          __    __                        
/\  _`\              /\ \        /\ \  /\ \                       
\ \ \L\_\__  _  __  _\ \ \/'\    \ `\`\\/'/ ___     ___     ___   
 \ \  _\/\ \/'\/\ \/'\\ \ , <     `\ `\ /' / __`\  / __`\  /'___\ 
  \ \ \/\/>  </\/>  </ \ \ \\`\     `\ \ \/\ \L\ \/\ \L\ \/\ \__/ 
   \ \_\ /\_/\_\/\_/\_\ \ \_\ \_\     \ \_\ \____/\ \____/\ \____\
    \/_/ \//\/_/\//\/_/  \/_/\/_/      \/_/\/___/  \/___/  \/____/
    ''')

    print("\033[35m")
    print(r'''
                                                Release 0.0.1    
                                                Powered by Horika, 
                                                Supported by Sarina
    ''')
def main():
    PrintLogo()
    print("\n\033[33m****** 欢迎使用 \033[31mFxxk Yooc\033[33m 易班优课免题库自动答题脚本 ******\n")
    print("*注意* 该脚本只适合易班优课可以无限答题的考试!!!")
    print("       使用脚本前请确保当前考试不在进行中!!!")
    print("       如果答题失败,请过五分钟之后再次尝试,如果还是不行,请联系我更新脚本!!!")
    print("       该脚本免题库的原理是通过反复答题来自我更新题库,所以答题次数越多,分数越高!!!")
    print("       短时间内答题次数过多容易被屏蔽造成答题失败,请不要贪心!!!\n")
    try:
        start()
    except Exception as e:
        print("答题失败:",e)


if __name__ == "__main__":

    main()

