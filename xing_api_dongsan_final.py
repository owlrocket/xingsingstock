from 강사용 import * 

import win32com.client # 
import pythincom 
import time
import threading
import random

#앞으로 사용하게 될 변수들을 모안 놓는다. 
class MyObjects:
    server = "hts" # htes: 실투자, demo : 모의투자
    tr_ok = False # TR요청
    real_ok = False #실시간 요청 
    acc_num = 계좌번호 
    acc_pw = 계좌비밀번호
    
    t8436_list = [] #종목코드 모아놓는 list 
    t0424_dict = [] #잔고내역2 종목들 모아 놓은 딕셔너리
    K3_dict = {} #종목의 체결정보들 모아 놓은 딕셔너리
    HA_dict = {} #종목의 호가잔량을 모아 놓은 딕셔너리 
    # avg_9_dict = {} #10일 이동평균선 계산을 위해서 9일치 종가의 합을 가진다. 
    min_dict = {} # 분봉 데이터를 모아 놓은 dict, {"종목코드": [[시간, 시가, 고가, 저가, 종가],[시간, 시가, 고가, 저가, 종가],...]}
    
    ########### 요청 함수 모음 
    tr_event = None #TR요청에 대한 API 정보 
    real_event = None #실시간 요청에 대한 API 정보 
    
    t8412_request = None # 차트데이터 조회 요청 함수 (분봉데이터요청)
    t0424_request = None # 잔고내역2 조회 요청함수 
    CSPAT00600_request = None # 신규주문 요청함수
    ######################################
    
    #################기타 변수들 
    cnt = 1 #주문 종목 카운트 
    qty = 5 #종목 몇개 살 건가? 
    mesu_order_ing = False # 연속으로 매수주문이 들어가는 것을 방지 
    medo_order_ing = False # 연속으로 매도주문이 들어가는 것을 방지 
    
    
  
#실시간으로 수신 받는 데이터를 다루는 구간 
class XR_event_handler: 
    
    def OnReceiveRealData(self, code):
        
        if code == "K3_":
            
            shcode = self.GetFieldData("OutBlock", "shcode")
            
            if shcode not in MyObjects.K3_dict.Keys():
                MyObjects.K3_dict[shcode] = {}
                MyObjects.K3_dict[shcode]["이평선보다아래"] = False #일단 이건 이평선 아래에서 올라가는 종목을 매매하는거
                
            
            #K3 관련 실시간 수신
            tt = MyObjects.K3_dict[shcode]
            tt["체결시간"] = self.GetFieldData("OutBlock", "chetime")
            tt["등락율"] = float(self.GetFieldData("OutBlock", "drate"))
            tt["현재가"] = int(self.GetFieldData("OutBlock", "price"))
            tt["시가"] = int(self.GetFieldData("OutBlock", "open"))
            tt["고가"] = int(self.GetFieldData("OutBlock", "high"))
            tt["저가"] = int(self.GetFieldData("OutBlock", "low"))
            tt["누적거래량"] = int(self.GetFieldData("OutBlock", "volume"))
            tt["매도호가"] = int(self.GetFieldData("OutBlock", "offerho"))
            tt["매수호가"] = int(self.GetFieldData("OutBlock", "bidho"))
            
            #분봉으로 10이평선 그리는거 9일합 + 오늘 현재가
            # 다 썼더니 실시간으로 분봉 누적한다고 쓸일이 없다함 
            # avg_10_price = 0 
            # if shcode in MyObjects.avg_9_dict.keys():
            #     add_9_price = sum(MyObjects.avg_9_dict[shcode])
            #     avg_10_price = (add_9_price + tt["현재가"]) / 10
            #     avg_10_price = ing(avg_10_price)
            # tt["10이동평균선"] = avg_10_price
            # print("10이동평균선 가격 %s" % avg_10_price, flush=True)
            
            chetime = tt["체결시간"]
            price = tt["현재가"]
            open = tt["시가"]
            
            #초기값으로 정한다. 
            if shcode not in MyObjects.min_dict.keys():
                MyObjects.min_dict[shcode] = [] #{"종목코드":[[시간, 시가, 고가, 저가, 종가],[시간, 시가, 고가, 저가, 종가], ...]}
                min_list = [chetime, open, price, price, price, price] #처음 1분봉과 2분봉은 안쓸거임, price는 시가, 고가, 저가, 종가 넣을거임
                MyObjects.min_dict[shcode].append(min_list)
                
            # max = len(MyObjects.min_dict[shcode])
            last_time = MyObjects.min_dict[shcode][-1][0] #리스트의 가장 마지막 시간

            last_t = datetime.datetime.strptime(last_time[0:4], '%H%M').time() # 마지막 1분봉 체결 시간
            last_hour, last_min = last_t.hour, last_t.minute
            last_min = (last_min + 60*last_hour)
            
            current_t = datetime.datetime.strptime(chetime[0:4], '%H%M').time() # 현재 체결시간
            current_hour, current_min = current_t.hour, current_t.minute
            current_min = (current_min + 60*current_hour)
            
            diff_min = current_min - last_min # 1분이 지났는지 확인하느거
            
            if diff_min >= 0: #1분봉이 새로 만들어졌단의미 
                # 1분 더해주는 용도 
                add_min = datetime.timedelta(minutes=1)
                
                #55분 이후에 59분, 즉 56, 57 ,58분이 비었다. 그러므로 59분-55분 = 4분이고, for문으로 돌린다. 
                #그래서 55분의 종가 데이터로 56, 57, 58분이 채워진다. 
                for i in range(diff_min): # 몇분 후에 나올 수도 있으니깐, 그 사이도 채워준다. 
                
                    last_time = MyObjects.min_dict[shcode][-1][0] # 리스트의 가장 마지막 시간
                    chk_t = datetime.datetime.strptime(last_time[0:4], '%H%M') #마지막 분봉 이후로 넣어주
                    last_price = MyObjects.min_dict[shcode][-1][4] # 종가 
                    
                    next_min = chk_t + add_min # 마지막 분봉에서 더해준다. 
                    next_min = next_min.strftime("%H%M00")
                    min_list = [next_min, last_price, last_price, last_price, last_price]
                    MyObjects.min_dict[shcode].append(min_list)
                    
                #다음 1분봉 만들 준비를 한다. 
                last_time = MyObjects.min_dict[shcode][-1][0] # 리스트의 가장 마지막 시간
                chk_t = datetime.datetime.strptime(last_time[0:4], '%H%M')# 마지막 분봉 이후로 넣어주기 
                
                next_min = chk_t + add_min # 마지막 분봉에서 더해준다. 
                next_min = next_min.strftime("%H%M00")
                min_list = [next_min, price, price, price, price]
                MyObjects.min_dict[shcode].append(min_list)
                
            elif diff_min < 0: # 아직 1분이 안지났으면, 1분봉 만들 준비를 한다. 
                last_high = MyObjects.min_dict[shcode][-1][2] # 고가 
                last_low = MyObjects.min_dict[shcode][-1][3] # 저가 
                
                MyObjects.min_dict[shcode][-1][4] = price # 종가 바뀜
                if last_high < price: 
                    MyObjects.min_dict[shcode][-1][2] = price # 고가 바뀜
                elif last_low > price: 
                    MyObjects.min_dict[shcode][-1][3] = price # 저가 바뀜
        
            #이동평균선 만들기 
            if shcode in MyObjects.min_dict.keys() and len(MyObject.min_dict[shcode]) >= 12: # 11보다 갖거나 크면 되는데 장중 시작시 안정적으로 보기위해 버릴라고 하는거임 
                sample_10 = MyObjects.min_dict[shcode][-10:].copy() # 10개만 뽑는다. 이데이터가 계산중 갱신되는거 예방
                add_price = 0
                for sample_list in sample_10 : 
                    add_price += sample_list[4] #종가 더해주기
                avg_10_price = add_price / 10 
                avg_10_price = int(avg_10_price)
                tt["10이동편균선"] = avg_10_price
           
            #분봉이 최소 12개 이상은 생겨야한다. 그때까지 주문안들어가게 
            if len(MyObjects.min_dict[shcoe]) < 12:
                return
            
            if tt["현재가"] < tt["10이동평균선"] and tt["이평선보다아래"] == False:
                print("골든크로스 되기 직전 가격: %s" % tt["현재가"], flush=True)
                tt["이평선보다아래"] = True
            print("%s, %s, $s" % (tt["현재가"], tt["10이동평균선"]))
            
                
            #HA 관련 실시간 수신            
            if shcode in MyObjects.HA_dict.Keys() \
                and MyObjects.HA_dict[shcode]["매수호가잔량4"] > 0 \
                    and MyObjects.HA_dict[shcode]["매도호가잔량4"] > 0 \
                        and MyObjects.cnt <= 1 and tt["현재가"] < 5000 \
                            and MyObjects.mesu_order_ing is False \
                                and shcode not in MyObjects.t0424_dict.key() \
                                    and tt["이평선보다아래"] is True \
                                        and tt["현재가"] > tt["10이동평균선"]: # 윗줄과 지금줄은 이평선 기준 아래있는지 조건 추가한거임 
                            
                print("호가잔량 데이터가 존재하고 호가 잔량 존재 : %s, 체결시간: %s" %  (shcode, tt["체결시간"]), flush=True)
                MyObjects.mesu_order_ing = True
                MyObjects.cnt += 1
                MyObjects.CSPAT00600_request(AcntNo=MyObjects.acc_num, InptPwd=MyObjects.acc_pw, IsuNo=shcode, OrdQty=MyObjects.qty, BnsTpCode="2")
         
            elif shcode in MyObjects.HA_dict.Keys() \
                and MyObjects.HA_dict[shcode]["매수호가잔량4"] > 0 \
                    and MyObjects.HA_dict[shcode]["매도호가잔량4"] > 0 \
                        and MyObjects.medo_order_ing is False \
                            and shcode not in MyObjects.t0424_dict.key() : 
                
                print("매도주문 요청구간: %s, 체결시간: %s" % (shcode, tt["체결시간"]), flush=True)
                
                earning_rate = MyObjects.t0424_dict[shcode]["수익률"]
                qty = MyObjects.t0424_dict[shcode]["매도가능수량"]
                
                if earning_rate > 10.0 or earning_rate < -10.0 : 
                    MyObjects.medo_order_ing = True
                    MyObjects.cnt -= 1
                    MyObjects.CSPAT00600_request(AcntNo=MyObjects.acc_num, Inptpwd=MyObjects.acc_pw, IsuNo=shcode, OrdQty=qty, BnsTpCode="1")

                    
        elif code == "HA_":
            
            shcode = self.GetFieldData("OutBlock", "shcode")
            
            if shcode not in MyObjects.HA_dict.Keys():
                MyObjects.HA_dict[shcode] = {}
            
            tt = MyObjects.HA_dict[shcode]
            tt["매수호가잔량4"] = int(self.GetFieldData("OutBlock", "bidrem4"))
            tt["매도호가잔량4"] = int(self.GetFieldData("OutBlock", "offerrem4"))
            
        elif code == "SC0":
            ordno = self.GetFieldData("OutBlock", "ordno") #주문번호 
            ordqty = self.GetFieldData("OutBlock", "ordgb") #주문수량 
            ordgb = self.GetFieldData("OutBlock", "ordgb") #주문가격 
            shtcode = self.GetFieldData("OutBlock", "shtcode") #종목코드 7자리 

            
            print("주문접수 SC0, 주문번호: %s, 주문수량: %s, 주문구분: %s, 종목코드: %s" % (ordno, ordqty, ordgb, shtcode), flush=True)
            
        elif code == "SC1":
            ordno = self.GetFieldData("OutBlock", "ordno") #주문번호 
            execqty = self.GetFieldData("OutBlock", "execqty") #체결수량 
            execprc = self.GetFieldData("OutBlock", "execprc") #체결가격 
            shtcode = self.GetFieldData("OutBlock", "shtcode") #종목코드 7자리  
            
            print("주문체결 SC1, 주문번호: %s, 체결수량: %s, 주문구분: %s, 종목코드: %s" % (ordno, execqty, execprc, shtcode), flush=True)
        

# TR 요청 이후 수신결과 데이터를 다루는 구간 
class XQ_event_handler:
    def OnReceiveData(self, code):
        print("%s 수신" % code, flush=True)
        
        if code == "t8436":
            occures_count = self.GetBlockCount("t8436OutBlock")
            print("종목 갯수: %s" % occurs_count, flush=True)
            for i in range(occurs_count, flush=True):
                shcode = self.GetFieldData("t8436OutBlock", "shcode", i)
                MyObjects.t8436_list.append(shcode)
                
            print("종목 리스트: %s" % MyObjects.t8436_list, flush=True)
            MyObjects.tr_ok = True
        
        elif code == "t8412": #분봉 data 요청
            
            shcode = self.GetFieldData("t8412OutBlock", "shcode", 0) #단축코드 
            cts_date = self.GetFieldData("t8412OutBlock", "cts_date", 0) #연속일자 
            cts_time = self.GetFieldData("t8412OutBlock", "cts_time", 0) #연속시간 
            
            close_list = [] #분봉종가 모으기 
            for i in range(occurs_count-1):
                
                date = self.GetFieldData("t8412OutBlock1", "date", i) 
                time = self.GetFieldData("t8412OutBlock1", "time", i) 
                close = self.GetFieldData("t8412OutBlock1", "close", i) 
                close = int(close)
                
                close_list.append(close) #종가를 담아서 나중에 이평선에 사용
            
            MyObjects.avg_9_dict[shcode] = close_list
            print(MyObjects.avg_9_dict, flush=True)
                
            # 과거 데이터를 더 가져오고 싶을 때는 연속조회를 해야한다. 
            if self.IsNext is True: #과거 데이터가 더 존재한다. 
                print("과거 데이터가 더 있다. 연속조회 기준 날짜: %s" % cts_date, flush=True)
                MyObjects.t8412_request(shcode=shcode, cts_date=cts_date, cts_time=cts_time, next=self.IsNext)
            elif self.IsNext is False:
                MyObjects.tr_ok = True

        elif code == "t0424":
            
            cts_expcode = self.GetFieldData("t0424OutBlock", "cts_expcode", 0)  
            
            MyObjects.t0424_dict.clear() #잔고내역이 있는거나 없는거로 인식하고 추가 매수/매도 주문되는거 예방?할때
            occurs_count = self.GetBlockCount("t0424OutBlock1") 
            for i in range(occurs_count):
                expcode = self.GetFieldData("t0424OutBlock1", "expcode", i) 
                
                if expcode not in MyObjects.t0424_dict.keys(): 
                    MyObjects.t0424_dict[expcode] = {}
                    
                tt = MyObjects.t0424_dict[expcode]
                tt["잔고수량"] = int(self.GetFieldData("t0424OutBlock1", "janqty", i))
                tt["매도가능수량"] = int(self.GetFieldData("t0424OutBlock1", "mdposqt", i))
                tt["평균단가"] = int(self.GetFieldData("t0424OutBlock1", "pamt", i))
                tt["종목명"] = self.GetFieldData("t0424OutBlock1", "hname", i)
                tt["종목구분"] = self.GetFieldData("t0424OutBlock1", "jonggb", i)
                tt["수익률"] = float(self.GetFieldData("t0424OutBlock1", "sunikrt", i))
                
                print("잔고내역 %s" % tt, flush=True)
                
'''
여기는 잔고 클리어 로 사용안함             
            #과거 데이터를 더 가져오고 싶을 때는 연속조회를 해야한다. 
            if self.IsNext is True: #과거 데이터가 더 존재한다. 
                MyObjects.t0424_request(cts_expcode=cts_expcode, next=self.IsNext)
            elif self.IsNext is False:
'''               
                MyObjects.mesu_order_ing = False
                MyObjects.medo_order_ing = False
                MyObjects.tr_ok = True
                
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
            
        MyObjects.tr_event = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", XQ_event_handler) 
        MyObjects.tr_event.ResFileName = "C:/eBEST/xingAPI/Res/t8436.res" #dev센터에서 xingAPI/Res에 res 파일로 저장하는것
        MyObjects.tr_event.SetFieldData("t8436InBlock", "gubun", 0, "2")
        MyObjects.tr_event.Request(False) 
        
        MyObjects.tr_ok = False 
        while MyObjects.tr_ok is False: 
            pythoncom.PumpWaitingMessages()
            
        MyObjects.tr_event.ResFileName = "C:/eBEST/xingAPI/Res/t8412.res" 
        MyObjects.t8412_request = self.t8412_request 
        start = random.randrange(1000) #1000까지중 random으로 뽑는다.
        end = start + 1000 #100개만 보겠다. 
        for shcode in MyObjects.t8436_list[start:end]: #for문으로 분봉요청하는거
            MyObjects.t8412_request(shcode=shcode, cts_date="", cts_time="", next=False)
        
        MyObjects.t8412_request(shcode"003000", cts_date="", cts_time="", next=False)
        
        #잔고내역 업데이트
        MyObjects.tr_event.ResFileName = "C:/eBEST/xingAPI/Res/t0424.res" 
        MyObjects.t0424_request = self.t0424_request 
        MyObjects.t0424_request(cts_expcode="", next=False)
        
        #챕터 4-1-1 주문을 넣어보자
        MyObjects.CSPAT00600_event = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", XQ_event_handler)
        MyObjects.CSPAT00600_event.ResFileName = "C:/eBEST/xingAPI/Res/CSPAT00600.res"
        MyObjects.CSPAT00600_request = self.CSPAT00600_request
        
        MyObjects.SC0_event = win32com.client.DispatchWithEvents("XA_DataSet.XAReal", XR_event_handler)
        MyObjects.SC0_event.ResFileName = "C:/eBEST/xingAPI/Res/SC0.res"
        MyObjects.SC0_event.AdviseRealData()
       
        MyObjects.SC1_event = win32com.client.DispatchWithEvents("XA_DataSet.XAReal", XR_event_handler)
        MyObjects.SC1_event.ResFileName = "C:/eBEST/xingAPI/Res/SC1.res"
        MyObjects.SC1_event.AdviseRealData()
        
                
        MyObjects.real_event = win32com.client.DispatchWithEvents("XA_DataSet.XAReal", XR_event_handler)
        MyObjects.real_event.ResFileName = "C:/eBEST/xingAPI/Res/K3_.res"
        for shcode in MyObjects.t8436_list:
            print("체결정보 종목 등록 %s" % shcode, flush=True)
            MyObjects.real_event.SetFieldData("Inblock", "shcode", shcode)
            MyObjects.real_event.AdviseRealData() 
                                                               
        MyObjects.real_event_ha = win32com.client.DispatchWithEvents("XA_DataSet.XAReal", XR_event_handler)
        MyObjects.real_event_ha.ResFileName = "C:/eBEST/xingAPI/Res/HA_.res"
        for shcode in MyObjects.t8436_list:
            print("호가잔량 종목 등록 %s" % shcode, flush=True)
            MyObjects.real_event_ha,SetFieldData("Inblock", "shcode", shcode)
            MyObjects.real_event_ha.AdviseRealData() 
            
        self.t0424_loop() # 동산이 추가한함수 쓰레드 관련
        
        
            
        while MyObjects.real_ok is False:
            pythoncom.PumpWaitingMessages()
            
                   
    def t8412_request(self, shcode=None, cts_date=None, cts_time=None, next=None):
        
        time.sleep(1.1)
        
        MyObjects.tr_event.SetFieldData("t8412InBlock", "shcode", 0, shcode)
        MyObjects.tr_event.SetFieldData("t8412InBlock", "ncnt", 0, 1)
        MyObjects.tr_event.SetFieldData("t8412InBlock", "qrycnt", 0, 10) #데이터 가지고오는 수량
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
            
    def t0424_request(self, cts_expcode=None, next=None):
        
        time.sleep(1.1)
        
        MyObjects.tr_event.SetFieldData("t0424InBlock", "accno", 0, MyObjects.acc_num)
        MyObjects.tr_event.SetFieldData("t0424InBlock", "passwd", 0, MyObjects.acc_pw)
        MyObjects.tr_event.SetFieldData("t0424InBlock", "prcgb", 0, "1")
        MyObjects.tr_event.SetFieldData("t0424InBlock", "chegb", 0, "2")
        MyObjects.tr_event.SetFieldData("t0424InBlock", "dangb", 0, "0")
        MyObjects.tr_event.SetFieldData("t0424InBlock", "charge", 0, "1")
        MyObjects.tr_event.SetFieldData("t0424InBlock", "cts_expcode", 0, "")
        
        MyObjects.tr_event.Request(next)
        
        MyObjects.tr_ok = False 
        while MyObjects.tr_ok is False:
            pythoncom.PumpWaitingMessages()            
     
    #주문을 넣어보자 
    def CSPAT00600_request(self, AcntNo=None, InptPwd=None, IsuNo=None, OrdQty=0, BnsTpCo=None):
         
        MyObjects.CSPAT00600_event.SetFieldData("CSPAT00600InBlock1", "AcntNo", 0, AcntNo) #계좌넘버
        MyObjects.CSPAT00600_event.SetFieldData("CSPAT00600InBlock1", "InptPwd", 0, InptPwd) #비밀번호
        
        if MMyObjects.server =="demo":
            IsuNo = "A"+IsuNo
            
        MyObjects.CSPAT00600_event.SetFieldData("CSPAT00600InBlock1", "IsuNo", 0, IsuNo) #종목번호
        MyObjects.CSPAT00600_event.SetFieldData("CSPAT00600InBlock1", "OrdQty", 0, OrdQty) #주문수량
        MyObjects.CSPAT00600_event.SetFieldData("CSPAT00600InBlock1", "OrdPrc", 0, 0) #주문가
        MyObjects.CSPAT00600_event.SetFieldData("CSPAT00600InBlock1", "BnsTpCode", 0, BnsTpCode) #1:매도, 2:매수
        MyObjects.CSPAT00600_event.SetFieldData("CSPAT00600InBlock1", "OrdprcPtnCode", 0, "03") #호가유형코드, 03:시장가 
        MyObjects.CSPAT00600_event.SetFieldData("CSPAT00600InBlock1", "MgntrnCode", 0, "000") #신용거래코드,
        MyObjects.CSPAT00600_event.SetFieldData("CSPAT00600InBlock1", "LoanDt", 0, "") #대출일
        MyObjects.CSPAT00600_event.SetFieldData("CSPAT00600InBlock1", "OrdCndiTpCode", 0, "0") #주문조건구분 0 :없음, 1:IOC, 2:FOK

        err = MyObjects.CSPAT006000_event.Request(False)
        if err < 0:
            print("\nXXXXXXXXXXXXXXX "
                  "\nCSPAT00600 주문에러"
                  "\n계좌번호: %s"
                  "\n종목코드: %s"
                  "\n주문수량: %s"
                  "\n매매구분: %s"
                  "\n주문에러: %s"
                  "\n\n" % (AcntNo, IsuNo, OrdQty, BnsTpCode ,err), flush=True)
                           
        else:
            print("\n============= "
                  "\nCSPAT00600 주문 실행"
                  "\n계좌번호: %s"
                  "\n종목코드: %s"
                  "\n주문수량: %s"
                  "\n매매구분: %s"
                  "\n주문에러: %s"
                  "\n\n" % (AcntNo, IsuNo, OrdQty, BnsTpCode ,err), flush=True)

    def t0424_loop(self):
        
        MyObjects.t0424(cts_expcode="", next=False)
        threading.Timer(10, self.t0424_loop).start() # 10초후 잔고내역요청 반복하란의미
        
if __name__ == "__main__":
    Main()


    
    
