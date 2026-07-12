import random
import numpy as np
import re

class Colors:
    GREEN = '\033[32m'
    RED = '\033[31m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    RESET = '\033[0m'

class Critical:
    def __init__(self, macd0, macd1, ema12, ema26, extreme2, L2, M2, extreme3,action):
        self.action = action #名称
        self.macd0 = macd0 #临界位置的macd
        self.macd1 = macd1 #翻转后的初始macd序列
        self.ema12 = ema12 #临界处的ema12快线
        self.ema26 = ema26 #临界处的ema26慢线
        self.extreme2 = extreme2 #第二次背离的最低点作为参考点
        self.extreme3 = extreme3 #第三次背离的最低点作为参考点（测试结果参考点）
        self.L2 = L2 ##第二次背离的macd序列长度
        self.M2 = M2 ##第二次背离的macd序列深度

    def to_line(self):
        macd1_str = str([round(x, 2) for x in self.macd1])
        return (f"{self.action}\n"
                f"macd0 = {self.macd0:.2f}\n"
                f"macd1 = {macd1_str}\n"
                f"ema120 = {self.ema12:.2f}\n"
                f"ema260 = {self.ema26:.2f}\n"
                f"L2 = {self.L2}\n"
                f"M2 = {self.M2:.2f}\n"
                f"extreme2 = {self.extreme2:.2f}\n"
                f"extreme3 = {self.extreme3:.2f}\n"
                f"\n"
                f"\n"
                )
    
    def do_benchmark(self,b):
        guess_L = list((set([int(self.L2/2) , int(self.L2/2) + (self.L2%2)])))
        if self.L2 <=10 :
            guess_L = [self.L2 - 1]
        
        #guess_M = [float(self.M2)*40/100, float(self.M2)*50/100, float(self.M2)*55/100]
        guess_M = [i * float(self.M2)/100 for i in range(45,56,1)] #lbb则采用所有可能结果的中心值
        #参考值8/24, 10.5/24, 13/24

        if self.macd0 * self.macd1[0] > 0:
            #print(f"macd1 activated...")
            #如果波包没有经过零轴,macd0和macd1同号，那么就以macd0为基准开始进行计算
            b = True
            self.macd1[0] =self.macd0

        v,s = task(guess_L,guess_M, self.ema12,self.ema26, self.macd0, self.macd1,b)

        sign = self.M2/abs(self.M2)
        lbs = [a + sign * b for a,b in zip(v,s)]
        lbl = min(lbs)
        lbu = max(lbs)
        #lbb  = (lbl + lbu)/2
        lbb = sum(lbs)/len(lbs)
        action = (self.action).replace("#","").replace(" ","")
        print(  f"{action:<16} " 
                f"{Colors.GREEN}vertx>{Colors.RESET} "
                f"{self.extreme2:<8.1f} {self.extreme3:<8.1f} "
                f"{Colors.GREEN}intrvl>{Colors.RESET} ({lbl:<8.1f} {lbb:<8.1f} {lbu:<8.1f})", 
                end=" ")
        
        if self.M2 < 0:
            if (lbb > self.extreme2):
                #如果第三次预测的最低点没有出现新低，放弃
                if self.extreme2*0.995 > self.extreme3 :
                    margin  = round(100-100*self.extreme3 / (0.995*self.extreme2),2)
                    if self.extreme2*0.995*0.98 < self.extreme3:
                        #在前低下方0.5%建仓时，在2%的止损区间捕捉到第三次背离的最低点
                        print(f"{Colors.CYAN}[catch<suspend><{margin}%>]{Colors.RESET}")
                    else:
                        #直接止损
                        print(f"{Colors.RED}[fatal<2+suspend>]{Colors.RESET}")
                else:
                    print("fail<trigger+suspend>")
                return 
            if(0.99*lbb < self.extreme3 < lbb):
                #第三次背离在估算区间中且命中1%最优目标
                margin = round(100-100*self.extreme3/lbb,2)
                if lbl < self.extreme3 < lbu :
                    #完美命中
                    print(f"{Colors.CYAN}[catch<1!><{margin}%>]{Colors.RESET}")
                else:
                    print(f"{Colors.CYAN}[catch<1><{margin}%>]{Colors.RESET}")
            else:
                #第三次背离没有命中区间
                margin = round(100-100*self.extreme3/lbb,2)
                if  0.98*lbb < self.extreme3 < lbb :
                    #命中2%的最大允许止损区间
                    print(f"{Colors.CYAN}[catch<2><{margin}%>]{Colors.RESET}")
                else:
                    if lbb < self.extreme3:
                        #没有触发建仓
                        print("[fail<trigger>]")
                    else:
                        #直接触发止损
                        print(f"{Colors.RED}[fatal<2>]{Colors.RESET}") 
        else:
            if (lbb < self.extreme2):
                #如果第三次预测的最高点没有出现新高，放弃
                if self.extreme2*1.005 < self.extreme3 :
                    margin  = round(100*self.extreme3/(self.extreme2*1.005)-100,2)
                    if self.extreme2*1.005*1.02 > self.extreme3:
                        #在前低上方0.5%建仓时，在2%的止损区间捕捉到第三次背离的最高点
                        print(f"{Colors.CYAN}[catch<suspend><{margin}%>]{Colors.RESET}")
                    else:
                        #直接止损
                        print(f"{Colors.RED}fatal<2+suspend>{Colors.RESET}")
                else:
                    #不能够触发建仓
                    print("fail<trigger+suspend>")
                return 
            
            if( 1.01*lbb > self.extreme3 > lbb):
                #第三次背离在估算区间中且命中1%最优目标
                margin = round(100*self.extreme3/lbb-100,1)
                if lbl < self.extreme3 < lbu:
                    print(f"{Colors.CYAN}[catch<1!><{margin}%>]{Colors.RESET}")
                else:
                    print(f"{Colors.CYAN}[catch<1><{margin}%>]{Colors.RESET}")
            else:
                #第三次背离没有命中区间
                margin = round(100*self.extreme3/lbb-100,1)
                if  1.02*lbb > self.extreme3 > lbb :
                    #命中2%的最大允许止损区间
                    print(f"{Colors.CYAN}[catch<2><{margin}%>]{Colors.RESET}")
                else:
                    if lbb > self.extreme3:
                        #没有触发建仓
                        print("[fail<trigger>]")
                    else:
                        #直接触发止损
                        print(f"{Colors.RED}[fatal<2>]{Colors.RESET}") 

def main():
    consol()
    # 输入macd即将由正数翻转为负数或者由负数翻转为正数前的最后一个macd值，记为macd0。
    # 输入macd0 时刻的快慢线数值ema120/ema260
    # 估算的macd包络长度L和峰值M
    # 如果已经出现翻转macd，带入前i个翻转值 macd1 用来给出更强求解约束。

def task(Ls,Ms, ema120,ema260, macd0, macd1, b):
    varr = []
    sarr = []
    for l in Ls:
        for m in Ms:
            t= []
            for n  in range(1,200):
                if b == False:
                    macd1 = []
                macdx = rand_envl(l,m,macd1)
                t.append(solv(macdx, macd0, ema120, ema260))
            avg = sum(t)/len(t)
            s = pow(sum([pow((x-sum(t)/len(t)),2) for x in t])/len(t),0.5)
            varr.append(avg)
            sarr.append(s)
    return varr, sarr
    
def rand_envl(L,M,macd1):
    L1 = int(L/2) + random.choice([0,L%2]) 
    L1x = L1 - len(macd1)
    L2 = L-L1 + 1
    r1x = np.random.random(L1x)
    r2 = np.random.random(L2)

    r1s = []
    if len(macd1) >0 :
        r1sx = [((float(M)-macd1[-1]) * x *0.99/max(r1x)) + macd1[-1] for x in r1x]
        r1s = macd1 + r1sx
    else:
        r1sx = [((float(M)) * x *0.99/max(r1x))  for x in r1x]
        r1s = r1sx

    r2s = [ float(M) * x * 0.99/ max(r2) for x in r2]

    b = True
    if (M > 0):
        b = False
    r1s.sort(reverse= b)
    r2s.sort(reverse= not b)
    rarrs = r1s + r2s[1:]
    return rarrs

def solv(macdx,macd0,ema120,ema260):
    alpha = float(2/(12+1))
    beta = float(2/(26+1))
    gamma = float(2/(9+1))
    arr = []

    for a in macdx:
        t = float(a) - (1-gamma)*macd0+(1-gamma)*(alpha*ema120-beta*ema260)
        t = t/(1-gamma)/(alpha-beta)
        arr.append(t)
        macd0 = a
        ema120 = alpha*t + (1-alpha)*ema120
        ema260 = beta*t + (1-beta)*ema260
        #print("macd",macd0,"pric",t)
    if (sum(macdx)<0):
        return min(arr)
    else:
        return max(arr)

def parse_benchmark(filepath):
    criticals = []
    with open(filepath, 'r') as f:
        lines = f.readlines()
    data = {}
    action = ""
    for line in lines:
        line = line.strip()
        if not line :
            continue
        if line.startswith('%'):
            #测试中的注释
            continue
        if line.startswith('#'):
            #行动标志
            action = line
            continue
        if '=' in line:
            key, value = line.split('=')
            key = key.strip()
            value = value.strip()
            if key == 'macd1':
                value = [float(value.strip('[]'))]
            elif key == 'L2':
                value = int(value)
            else:
                value = float(value)
            data[key] = value
        if all(k in data for k in ['macd0', 'macd1', 'ema120', 'ema260', 'extreme2', 'L2', 'M2', 'extreme3']):
            critical = Critical(
                action = action,
                macd0=data['macd0'],
                macd1=data['macd1'],
                ema12=data['ema120'],
                ema26=data['ema260'],
                extreme2=data['extreme2'],
                L2=data['L2'],
                M2=data['M2'],
                extreme3=data['extreme3'],
            )
            criticals.append(critical)
            write_back_sorted(criticals)
            data = {}
    return criticals

def consol():
    str = input()
    if(str == "test"):
        #回测所有benchmark
        benchmarking()
        return
    elif(str == "go"):
        #直接测试一组内置数据
        v,s = task([8],[4,5],4738.72,4722.74,-3.51,[],False)
        rr = [x+y for x,y in zip(v,s)]
        print([round(x,1) for x in rr])
        return
    else:
        #输入一组数据测试
        do_parsing()
        return

def  benchmarking():
    criticals = parse_benchmark('C:/Users/lambd/Desktop/重拳出击/benchmark.txt')
    for c in criticals:
        c.do_benchmark(False)
    return

def do_parsing():
    macd0 = float(input("macd0>"))
    ema12 = float(input("ema12>"))
    ema26 = float(input("ema26>"))
    macd1 = [float(x) for x in input("macd1").split()]
    Ls  = [int(x) for x in input("Ls>").split()]
    Ms  = [float(x) for x in input("Ms>").split()]
    task(Ls,Ms,ema12,ema26,macd0,macd1,True)

def write_back_sorted(criticals):
    criticals1 = sorted(criticals, key = lambda x : re.sub(r'\D', '', x.action),reverse=True)

    with open('C:/Users/lambd/Desktop/重拳出击/benchmark.txt', 'w', encoding='utf-8') as f:
        for c in criticals1:
            f.write(c.to_line() + '\n')
            
if __name__ == "__main__":
    main()
