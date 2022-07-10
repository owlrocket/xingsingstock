from 강사용 import * 

import win32com.client # 
import pythincom 
import time


# 앞으로 사용하게 될 변수들을 모안 놓는다. 
class MyObjects:
    server = "hts" # htes: 실투자, demo : 모의투자
    tr_ok = False # TR요청
    #기존에 login_ok로 한건 tr_ok로 변경 가능 (로그인도 tr요청중 하나임)하여 tr_ok로 변경 
    acc_num = 계좌번호 
    acc_pw = 계좌비밀번호
    
    t8436_list = [] #종목코드 모아놓는 list 
    
    ########### 요청 함수 모음 
    tr_event = None #TR요청에 대한 API 정보 


#실시간으로 수신 받는 데이터를 다루는 구간 
class XR_event_handler: 
    pass

# TR 요청 이후 수신결과 데이터를 다루는 구간 
class XQ_event_handler:
    
    def OnReceiveData(self, code):
        print("%s 수신" % code, flush=True)
        
        if code == "t8436":
            occures_count = self.GetBlockCount("t8436OutBlock")
            print("종목 갯수: %s" % occurs_count, flush=True)
            for i in range(occurs_count, flush=True): #모든 종목코드의 data를 반복
                shcode = self.GetFieldData("t8436OutBlock", "shcode", i) #이건 종목코드 받는건데, dev센터에서 제공하는 여러가지를 동일한 코드로작성하여 데이터 요청 할 수 있음 
                #uplmtprice = self.GetFieldData("t8436OutBlock", "uplmtprice", i) #예를 들어 상한가종목
                MyObjects.t8436_list.append(shcode)
                
            print("종목 리스트: %s" % MyObjects.t8436_list, flush=True)
            MyObjects.tr_ok = True
        
        elif code == "t8412":
            
            shcode = self.GetFieldData("t8412OutBlock", "shcode", 0) #단축코드 
            cts_date = self.GetFieldData("t8412OutBlock", "cts_date", 0) #연속일자 
            cts_time = self.GetFieldData("t8412OutBlock", "cts_time", 0) #연속시간 

            occurs_count = self.GetFieldCount("t8412OutBlock1")
            for i in range(occurs_count):
                
                date = self.GetFieldData("t8412OutBlock1", "date", i) 
                time = self.GetFieldData("t8412OutBlock1", "time", i) 
                close = self.GetFieldData("t8412OutBlock1", "close", i) 
                
            # 과거 데이터를 더 가져오고 싶을 때는 연속조회를 해야한다. 
            if self.IsNext is True: #과거 데이터가 더 존재한다. self는 xingAPI의 self임
                print("과거 데이터가 더 있다. 연속조회 기준 날짜: %s" % cts_date, flush=True)
                MyObjects.t8412_request(shcode=shcode, cts_date=cts_date, cts_time=cts_time, next=self.IsNext)
            elif self.IsNext is False:
                MyObjects.tr_ok = True                
    
    #요청이 잘됐는지 안됐는지 잘 받았는지 알려주는 함수 
    def OnReceiveMessage(self, systemError, messageCode, message):
        print("systemError: %s, messageCode: %s, message: %s" % (systemError, messageCode, message)
     

# 서버접속 및 로그인 요청 이후 수신결과 데이터를 다루는 구간 
class XS_event_handler:
    
    def OnLogin(self, szCode, szMsg):
        print("%s %s" % (szCode, szMsg), flush=True)
        if szCode == "0000":
            MyObjects.login_ok = True 
        else: 
            MyObjects.login_ok = False 
                    
    pass

#실행용 클래스 

class Main:
    def __init__(self):
        print("실행용 클래스이다.")
        
        session = win32com.client.DispatchWithEvents("XA_Session.XASession", XS_event_handler)
        session.ConnectServer(MyObjects.server + ".ebestsec.co.kr", 20001) # 서버 연결 
        session.Login(아이디, 비밀번호, 공인인증서, 0, False) # 서버 연결
        
        while MyObjects.tr_ok is False:
            pythoncom.pumpWaitingMessages ()
            
        #종목코드(전체list) 가져오기            
        MyObjects.tr_event = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", XQ_event_handler) #tr요청후 받은 데이터가 모이는곳 XQ_event_handler
        MyObjects.tr_event.ResFileName = "C:/eBEST/xingAPI/Res/t8436.res" #dev센터에서 xingAPI/Res에 res 파일로 저장하는것의 경로이고 여기 데이터그대로 가져오는것
        MyObjects.tr_event.SetFieldData("t8436InBlock", "gubun", 0, "0") #0전체,1코스피,2코스닥 
        MyObjects.tr_event.Request(False) #서버에 요청해라
        
        #tr요청후 데이터 받을때까지 false로 대기 (로그인 대기와 동일)
        MyObjects.tr_ok = False 
        while MyObjects.tr_ok is False: 
            pythoncom.PumpWaitingMessages()
            
        MyObjects.tr_event.ResFileName = "C:/eBEST/xingAPI/Res/t8412.res" 
        MyObjects.t8412_request = self.t8412_request #아래 함수를 이용해서 과거 데이터를 받기위한 함수
        MyObjects.t8412_request(shcode="003000", cts_date="", cts_time="", next = False) #함수에서 받은 데이터중 종목코드 003000에대해서 요청함

    def t8412_request(self, shcode=None, cts_date=None, cts_time=None, next=None):
        
        time.sleep(1.1)
        
        #dev센터의 InBlock form 대로 요청
        MyObjects.tr_event.SetFieldData("t8412InBlock", "shcode", 0, shcode)
        MyObjects.tr_event.SetFieldData("t8412InBlock", "ncnt", 0, 1)
        MyObjects.tr_event.SetFieldData("t8412InBlock", "qrycnt", 0, 500)
        MyObjects.tr_event.SetFieldData("t8412InBlock", "nday", 0, "0")
        MyObjects.tr_event.SetFieldData("t8412InBlock", "sdate", 0, "")
        MyObjects.tr_event.SetFieldData("t8412InBlock", "edate", 0, "당일")
        MyObjects.tr_event.SetFieldData("t8412InBlock", "cts_date", 0, cts_date)
        MyObjects.tr_event.SetFieldData("t8412InBlock", "cts_time", 0, cts_time)
        MyObjects.tr_event.SetFieldData("t8412InBlock", "comp_yn", 0, "N")
        
        MyObjects.tr_event.Request(next)
        
        MyObjects.tr_ok = False 
        while MyObjects.tr_ok is False:
            pythoncom.PumpWaitingMessages()


if __name__ == "__main__":
    Main()


    
    
