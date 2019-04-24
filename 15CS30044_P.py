#!/usr/bin/env python
# coding: utf-8

import sys
import queue

# global objects
operators = ['Add', 'Sub', 'Mul', 'Div']


# Info parsed after reading the Problem Statement
'''
Specifications from assignment statement :
    1. Only four types of instructions : ADD, SUB, MUL, DIV
    2. Two processing units : interger addition unit, integer multiplication unit
    3. Addition unit performs ADD and SUB : Both take 2 cycles
    4. Addition unit has 3 reservation stations : RS0, RS1, RS2
    5. Multiplication unit performs MUL and DIV : MUL takes 10 cycles and DIV takes 40 cycles
    6. Multiplication unit has 2 reservation stations : RS3, RS4
    7. The processor has eight registers : R0 - R7
    8. No same cycle issue-dispatch : dispatch then issue
    9. No same cycle capture-dispatch : dispatch then capture(chosen)
    10. RS which is freed in a cycle cannot be allocated in the same cycle : issue then dispatch(chosen)
    11. Capture then issue for RAT not being overwritten, issue then capture(chosen) to capture operands of newly issued instructions. Choosing the latter as first one easier to handle.
    12. So write in this order : issue then dispatch then capture, to handle 8 put info about when the instruction was issued and check this while dispatching, to handle 11 put info about when instruction was issued in RAT and don't overwrite if same cycle capture.
    13. During broadcast, multiplication unit has precedence over addition unit
    14. RS precedence according to the index. Lower the index of RS of a unit more precedence. Dispatch of both units can happen together.
    15. The instruction queue can hold upto a maximum of 10 instructions. Currently putting the instructions directly in the queue, can later transfer them to a list and then to a queue.
    16. (0: add; 1: sub; 2: multiply; 3: divide) , remember it is integer division.
    17. The operands and result can only be registers.
    18. Have put the instructions in a list for now, will then put the instructions in a queue of maxsize 10.
    19. Here, assumed that the register renaming process is already done, tomasulo takes care of it
'''

class inst :
    def __init__(self, op, res, op1, op2) :
        self.op = op
        self.res = res
        self.op1 = op1
        self.op2 = op2
    def show(self) :
        print('%s R%d, R%d, R%d'%(nameOperator(self.op), self.res, self.op1, self.op2))

def nameOperator(op) :
    global operators
    return operators[op]

class ratentry :
    def __init__(self, tag, c) :
        self.tag = tag
        self.c = c 
    def show(self) :
        print('tag : RS'+str(self.tag),'c',self.c)

class RS :
    def __init__(self) :
        self.busy = 0
        self.op = -1
        self.vj = 0
        self.vk = 0
        self.qj = -1
        self.qk = -1
        self.disp = 0
        self.c = -1 # c is the last cycle in which it was updated. Will be updated during issue and capture. To avoid same cycle issue-dispatch and capture-dispatch. Same cycle capture-dispatch probably won't happen so don't need to worry about that
    def show(self) :
        print('busy',self.busy,'op',self.op,'vj',self.vj,'vk',self.vk,'qj','RS'+str(self.qj),'qk','RS'+str(self.qk),'disp',self.disp,'c',self.c)

class ALU :
    def __init__(self) :
        self.busy = 0
        self.tag = -1 # RS
        self.op = -1
        self.op1 = 0
        self.op2 = 0
        # self.val = 0 # result value of operation # instead lets put result value in capture itself
        self.ready = -1 #last cycle of execution, in the next cycle we can capture the result. We first perform capture and then store the result to be captured in the next cycle.
    def show(self) :
        print('busy',self.busy,'tag','RS'+str(self.tag),'op',nameOperator(self.op),'op1',self.op1,'op2',self.op2,'ready',self.ready)

class BroadcastLines :
    def __init__(self) :
        self.busy = 0
        self.tag = -1
        self.val = 0
    def show(self) :
        print('busy',self.busy,'tag','RS'+str(self.tag),'val',self.val)

def init() :
    global rs
    global curinst
    global addunit
    global mulunit
    global resbuf
    global n
    global C
    global li
    global rat
    global rf
    global qi
    global iterli

    rs = []
    for i in range(5) :
        rs.append(RS())
    curinst = -1
    addunit = ALU()
    mulunit = ALU()
    resbuf = BroadcastLines()

    # Take input

    #f = open('input.txt','r')
    #lines = f.readlines()
    #f.close()

    n = int(input())  #lines[0]) #input()) # No. of instructions
    C = int(input())  #lines[1]) #input()) # No. of cycles of simulation
    li = [] # List of instructions, will put in a queue later
    for i in range(n) :
        ti = [int(str) for str in input().split()]
        ti = inst(*ti)
        li.append(ti)

    rat = [] # Register Address Table, -1 means to look at the Register file, each entry is a tuple (tag, c), c is the cycle in which the RAT entry was updated
    rf = [] # Register File
    for i in range(8) :
        rat.append(ratentry(-1,-1))
        rf.append(int(input()))

    qi = queue.Queue(10) # Queue of instructions
    iterli = 0           # iterator for li
    for iterli in range(len(li)) :
        qi.put(li[iterli])
        if qi.full() :
            break


def issue(c) :
    global curinst
    global li
    global iterli
    global rs
    global qi
    index = -1
    if curinst == -1 :
        if not qi.empty() :
            curinst = qi.get()
            if iterli != len(li)-1 :
                iterli += 1
                qi.put(li[iterli])
            #print('issue curinst check')
        else :
            return
    #print('--------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    #print('Current Instruction in queue')
    #print('--------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    #curinst.show()
    if curinst.op in [0, 1] : # Add or Sub
        for i in range(3) :
            if rs[i].busy == 0 :
                index = i
                break
        if index == -1 :
            return
        #print('curinst op add check')
    if curinst.op in [2, 3] : # Add or Sub
        for i in range(3,5) :
            if rs[i].busy == 0 :
                index = i
                break
        if index == -1 :
            return
        #print('curinst op mul check')
    
    # found our rs
    i = index
    rs[i].busy = 1
    rs[i].op = curinst.op
    if rat[curinst.op1].tag == -1 :
        rs[i].vj = rf[curinst.op1]
        rs[i].qj = -1
    else :
        rs[i].qj = rat[curinst.op1].tag
    if rat[curinst.op2].tag == -1 :
        rs[i].vk = rf[curinst.op2]
        rs[i].qk = -1
    else :
        rs[i].qk = rat[curinst.op2].tag
    rs[i].disp = 0
    rs[i].c = c
    rat[curinst.res].tag = i
    rat[curinst.res].c = c
    
    #rs[i].show()
    #rat[curinst.res].show()
    
    # remove current inst
    curinst = -1


def dispatch(c) :
    global addunit
    global mulunit
    if addunit.busy == 0 :
        for i in range(3) :
            if rs[i].busy == 1 and rs[i].disp == 0 and rs[i].c != c and rs[i].qj == -1 and rs[i].qk == -1 :
                rs[i].disp = 1
                # rs[i].c = c , not required for same cycle capture-dispatch as capture first checks disp and then c
                addunit.busy = 1
                addunit.tag = i
                addunit.op = rs[i].op
                addunit.op1 = rs[i].vj
                addunit.op2 = rs[i].vk
                addunit.ready = c+2-1 # -1 since last cycle of execution, capture can done in c+2
                #print('dispatch add unit check')
                #addunit.show()
                break
    if mulunit.busy == 0 :
        for i in range(3,5) :
            if rs[i].busy == 1 and rs[i].disp == 0 and rs[i].c != c and rs[i].qj == -1 and rs[i].qk == -1 :
                rs[i].disp = 1
                # rs[i].c = c , not required for same cycle capture-dispatch as capture first checks disp and then c
                mulunit.busy = 1
                mulunit.tag = i
                mulunit.op = rs[i].op
                mulunit.op1 = rs[i].vj
                mulunit.op2 = rs[i].vk
                if mulunit.op == 2 : # multiplication
                    mulunit.ready = c+10-1 # -1 since last cycle of execution, capture can done in c+2
                if mulunit.op == 3 : # division
                    mulunit.ready = c+40-1 # -1 since last cycle of execution, capture can done in c+2
                #print('dispatch mul unit check')
                #mulunit.show()
                break

def broadcast(c) :
    global resbuf
    global addunit
    global mulunit
    #print('capture entrance check',c)
    #resbuf.show()
    if resbuf.busy == 1 :
        resbuf.busy = 0
        for i in range(8) :
            if rat[i].tag == resbuf.tag and rat[i].c != c : # recently issued instruction should not be overwritten, this case takes place if a subsequent instruction has the same result register
                rat[i].tag = -1
                rf[i] = resbuf.val
                break # As there would be at a time atmax one register tagged with a reservation station
        for i in range(5) :
            if rs[i].busy == 1 and rs[i].disp == 0 :
                rs[i].c = c # redundant as next dispatch can happen only in next cycle and hence, capture-dispatch for an rs always will never happen in same cycle
                if rs[i].qj == resbuf.tag :
                    rs[i].qj = -1
                    rs[i].vj = resbuf.val
                if rs[i].qk == resbuf.tag :
                    rs[i].qk = -1
                    rs[i].vk = resbuf.val
        rs[resbuf.tag].busy = 0 # free the rs
        #print('capture resbuf broadcast check')
        #resbuf.show()
    
    # Broadcast mulunit's result first
    if mulunit.busy == 1 and mulunit.ready <= c :
        mulunit.busy = 0
        resbuf.busy = 1
        resbuf.tag = mulunit.tag
        if mulunit.op == 2 :
            resbuf.val = mulunit.op1*mulunit.op2
        if mulunit.op == 3 :
            resbuf.val = mulunit.op1//mulunit.op2
        #print('capture mulunit resbuf check')
        #resbuf.show()
        return
    
    if addunit.busy == 1 and addunit.ready <= c :
        addunit.busy = 0
        resbuf.busy = 1
        resbuf.tag = addunit.tag
        if addunit.op == 0 :
            resbuf.val = addunit.op1+addunit.op2
        if addunit.op == 1 :
            resbuf.val = addunit.op1-addunit.op2
        #print('capture addunit resbuf check')
        #resbuf.show()

def showstatus(c) :
    global rs
    global rf
    global curinst
    global qi
    print('--------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    if c == -1 :
        print('Status at the beginning of execution')
    else :
        print('Status after end of cycle',c+1)
    print('--------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    print('Reservation Stations :')
    print('--------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    print('\t\tBusy\t\tOp\t\tVj\t\tVk\t\tQj\t\tQk\t\tDisp')
    for i in range(5) :
        if rs[i].busy == 0 :
            print('RS%d\t\t%d'%(i,rs[i].busy))
            continue
        if rs[i].qj == -1 :
            vj = str(rs[i].vj)
            qj = ''
        else :
            vj = ''
            qj = 'RS' + str(rs[i].qj)
        if rs[i].qk == -1 :
            vk = str(rs[i].vk)
            qk = ''
        else :
            vk = ''
            qk = 'RS' + str(rs[i].qk)
        print('RS%d\t\t%d\t\t%s\t\t%s\t\t%s\t\t%s\t\t%s\t\t%d'%(i,rs[i].busy,nameOperator(rs[i].op),vj,vk,qj,qk,rs[i].disp))
    print('--------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    print('Register File and Register Alias Table')
    print('--------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    print('\t\tRF\t\tRAT')
    for i in range(8) :
        if rat[i].tag == -1 :
            tag = ''
        else :
            tag = 'RS' + str(rat[i].tag)
        print('%d:\t\t%d\t\t%s'%(i,rf[i],tag))
    print('--------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    print('Instruction Queue')
    print('--------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    if curinst != -1 :
        curinst.show()
    for i in range(qi.qsize()) :
        temp = qi.get()
        if curinst != -1 and i==9 :
            pass
        else :
            temp.show()
        qi.put(temp)
    print('--------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
    

def main() :
    init()
    print('--------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    print('Input Instructions')
    print('--------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    for i in li :
        i.show()
    print('--------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
    showstatus(-1)

    for c in range(C) :
        issue(c)
        dispatch(c)
        broadcast(c)
        showstatus(c)


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()

