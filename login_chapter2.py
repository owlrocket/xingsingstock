from dannysh import *
import win32com.client # com방식의 모듈을 import 
import pythoncom #파이썬으로 com을 코딩하기 위해 import


# 앞으로 사용하게 될 변수들을 모아 놓는다. 
class MyObjects:
    server = "hts" # htes: 실투자, demo : 모의투자
    tr_ok = False # TR요청 login_ok = False 는 서버 접속시 로그인 완료때까지 기다리는 변수로 나중에 True로 바뀌면 다음 요청 실행


#실시간으로 수신 받는 데이터를 다루는 구간 
class XR_event_handler: 
    pass

# TR 요청 이후 수신결과 데이터를 다루는 구간 
class XQ_event_handler:
    pass

# 서버접속 및 로그인 요청 이후 수신결과 데이터를 다루는 구간 
class XS_event_handler:
    
    def OnLogin(self, szCode, szMsg): #변수는 xingAPI하라는대로
        print("%s %s" % (szCode, szMsg), flush=True)
        if szCode == "0000": #로그인 성공시 0000이 됨
            MyObjects.login_ok = True 
        else: 
            MyObjects.login_ok = False 
                    
    pass

#실행용 클래스 

class Main:
    def __init__(self):
        print("실행용 클래스이다.")
        
        session = win32com.client.DispatchWithEvents("XA_Session.XASession", XS_event_handler)
        session.ConnectServer("hts.ebestsec.co.kr", 20001) # 서버 연결 
        session.Login(아이디, 비밀번호, 공인인증서, 0, False) # 서버 연결
        
        while MyObjects.tr_ok is False: #login_ok가 true될때까지 기다리게 무한 루프 돌리게 하기 위한 while
            pythoncom.PumpWaitingMessages ()
         

if __name__ == "__main__":
    Main()


    
    
