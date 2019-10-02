"""The butchered remains of the GLine robot software for SPEC control."""

import socket, select, time, threading, sys, serial, signal
import SpecClient
from SpecClient import SpecCommand
from SpecClient import SpecEventsDispatcher
import ClosableQueue, queue
import logging


soloSoftCommandQueue = ClosableQueue.CQueue()
soloSoftAnswerQueue = ClosableQueue.CQueue()

controlQueue = ClosableQueue.CQueue()

adxCommandQueue = ClosableQueue.CQueue()
adxAnswerQueue = ClosableQueue.CQueue()

logger = logging.getLogger('python')

class CommException(Exception):
    def __init__(self, value):
        self.parameter = value

    def __str__(self):
        return repr(self.parameter)

class AbortException(Exception):
    def __init__(self, value):
        self.parameter = value

    def __str__(self):
        return repr(self.parameter)

class MySpecCommand(SpecCommand.SpecCommandA):

    def __init__(self, command, host, thread):

        self.command = command
        self.host = host
        self.reply = None
        self.ready = None
        self.thread = thread

        SpecCommand.SpecCommandA.__init__(self, command, host)

    def connected(self):
        self.ready = True

    def disconnected(self):
        self.ready = False
        self.thread.abort()

    def getReady(self):
        return self.getReady

    def beginWait(self):
        print('Command sent to spec')

    def replyArrived(self, reply):
        print('Reply from spec1234: ', str(reply.data))
        print('Errorcode: ', str(reply.error))
        self.reply = reply

    def GetReply(self):
        reply = self.reply
        return reply

    def ClearReply(self):
        self.reply = None


class SpecCommThread(threading.Thread):

    def __init__(self, host):

        threading.Thread.__init__(self)

        self.isSpec = True
        self.host = host
        self.abortProcess = False
        self.answerCount = 0
        self.waitingForAnswer = False
        self.specCommand = None
        self.conLost = False
        self.exposure = False
        self.LEDOn = False

    def run(self):

        ############## CONNECT ON STARTUP ##############
        try:
            self.specCommand = MySpecCommand('', self.host, self)
            print('Connected to SPEC')
        except SpecClient.SpecClientError.SpecClientTimeoutError:
            self.specCommand = None
            controlQueue.put([('G', 'A LED_ERROR')])
            controlQueue.put([('G', 'A CONNECT_ERROR')])
            logger.exception("Caught exception in SoloComm:")

        ###############################################

        while True:
            commandList = adxCommandQueue.get()
            adxCommandQueue.task_done()

            print('SpecThread Processing : ', str(commandList))

            self.abortProcess = False
            self.exposure = False
            self.LEDOn = False

            for eachCommand in commandList:

                if self.abortProcess:
                    break

                try:
                    self.specCommand.ClearReply()
                    self.specCommand.executeCommand(eachCommand)
                    if eachCommand.split()[0] == 'rgseries':
                        controlQueue.put([('G', 'A STARTWATCH')])
                        self.exposure = True
                    if len(eachCommand.split())>1:
                        if eachCommand.split()[1] == 'mkdir':
                            self.LEDOn = True
                    answer = self.waitForAnswerFromSpec()
                    print('Received Answer From SPEC :', str(answer))
                except (AttributeError, SpecClient.SpecClientError.SpecClientNotConnectedError):
                    controlQueue.put([('G', 'A LED_ERROR')])
                    controlQueue.put([('G', 'A CONNECT_ERROR')])
                    self.abortProcess = True

            if not self.abortProcess and self.exposure and not self.LEDOn:
                controlQueue.put([('G', 'ADXDONE_EXP')])
            elif not self.abortProcess and not self.LEDOn:
                controlQueue.put([('G', 'ADXDONE_OK')])
            elif not self.abortProcess and self.LEDOn:
                controlQueue.put([('G', 'ADXDONE_LED_ON')])
            elif self.abortProcess and self.LEDOn:
                controlQueue.put([('G', 'ADXDONE_ABORT_DIR')])
            else:
                controlQueue.put([('G', 'ADXDONE_ABORT')])

    def waitForAnswerFromSpec(self):
        self.waitingForAnswer = True

        self.specCommand.ClearReply()
        print('Waiting for answer from SPEC...')
        while self.waitingForAnswer and self.abortProcess == False:
            SpecEventsDispatcher.dispatch()
            time.sleep(0.01)

            answer = self.specCommand.GetReply()
            if answer is not None:
                self.waitingForAnswer = False
                self.specCommand.ClearReply()
                return answer.getValue()
        if self.abortProcess:
            print('No longer waiting')
            self.specCommand.abort()
            answer = self.waitForAnswerFromSpecAbort()
            print('Got resonse from spec for abort: %s' % (answer))
            if self.exposure:
                controlQueue.put([('A', 'closes')])
            return 'Aborted'

    def waitForAnswerFromSpecAbort(self):
        waitingForAnswer = True
        sleeptime = 0.01
        loopmax = 1./sleeptime
        loopcount = 0

        self.specCommand.ClearReply()
        while waitingForAnswer and loopcount < loopmax:
            SpecEventsDispatcher.dispatch()
            time.sleep(0.01)

            answer = self.specCommand.GetReply()
            if answer is not None:
                waitingForAnswer = False
                self.specCommand.ClearReply()
                return answer.getValue()

            loopcount = loopcount + 1
        print('Waiting for abort response timed out!!!')

    def tryReconnect(self, TryOnce=False):
        reconnected = False

        if TryOnce:
            try:
                print('Trying to reconnect to SPEC...')
                self.specCommand = MySpecCommand('', self.host, self)
                reconnected = True
                print('Connected!')
                return True
            except SpecClient.SpecClientError.SpecClientTimeoutError:
                return False
        else:
            while not reconnected:
                try:
                    print('Trying to reconnect to SPEC...')
                    time.sleep(1)
                    self.specCommand = MySpecCommand('', host, self)
                    reconnected = True
                    print('Connected!')
                    return True
                except SpecClient.SpecClientError.SpecClientTimeoutError:
                    pass

    def setConnectionLost(self):
        self.conLost = True

    def abort(self):
        # self.specCommand.abort()
        self.abortProcess = True

def parseListOfCommands(self, cmdList):

    parsedCommandList = []

    for each in cmdList:

        command = parseCommand(each)
        parsedCommandList.append(command)

    return parsedCommandList

def parseCommandFile(filename):

    f = open(filename, 'r')

    commandList = []

    for eachLine in f:
        commandList.append(parseCommand(eachLine))

    return commandList

def parseCommand(cmd):
    splitLine = cmd.split()

    command = ''

    serv = splitLine[0].upper()

    if serv == 'R' or serv == 'S':
        pass
    else:
        raise IndexError

    if len(splitLine) > 2:
        command = splitLine[1] + ' ' + splitLine[2]
    else:
        command = splitLine[1]

    if command == 'CTRLZ':
        command = chr(26)
    if command == 'GETSYRPOS':
        command = 'aYQPR'
    if command == 'GETSYRBUSY':
        command = 'aE1R'

    if splitLine[1].upper() == 'UP':
        twosplit = splitLine[2].split(',')
        command = 'aWD'+twosplit[0]+'S'+twosplit[1]+'R'
    if splitLine[1].upper() == 'DOWN':
        twosplit = splitLine[2].split(',')
        command = 'aWP'+twosplit[0]+'S'+twosplit[1]+'R'
    if splitLine[1].upper() == 'SUP':
        twosplit = splitLine[2].split(',')
        command = 'aID'+twosplit[0]+'S'+twosplit[1]+'R'
    if splitLine[1].upper() == 'SDOWN':
        twosplit = splitLine[2].split(',')
        command = 'aIP'+twosplit[0]+'S'+twosplit[1]+'R'

    return [serv, command]

def waitFor(state):
    solostate = None

    while(solostate != state):
        time.sleep(1)
        soloSoftCommandQueue.put(('S', 'GETSTATUS'))
        answer = soloSoftAnswerQueue.get()
        solostate = answer[1]
        soloSoftAnswerQueue.task_done()



def initConnections(MainGui, host='128.84.182.214:6510'):
    ADXComm = SpecCommThread(host)


    ADXComm.setDaemon(True)
    ADXComm.start()

    Controller = ControlThread(ADXComm, MainGui)
    Controller.setDaemon(True)
    Controller.start()

    # return SSComm, Controller
    return Controller

class ControlThread(threading.Thread):

    def __init__(self, ADXComm, MainGUI):

        threading.Thread.__init__(self)

        self.ADXComm = ADXComm
        self.MainGUI = MainGUI

        self.abortProcess = False
        self.adxRead = True

        self.oldFilename = None

        self.oldDirectory = None

    def run(self):
        while self.MainGUI.listen_run_flag.is_set():
            if controlQueue.empty():
                self.MainGUI.queue_busy = False
                self.MainGUI.toggle_buttons()
            else:
                queue_item = controlQueue.get()
                if isinstance(queue_item, list):
                    commandList = queue_item
                    if len(commandList) == 1 and (commandList[0][1] == 'SAFETYCHECK' or commandList[0][0] == 'G'):
                        pass
                    else:
                        self.MainGUI.queue_busy = True
                        self.MainGUI.toggle_buttons()
                elif not self.MainGUI.queue_busy:
                    self.MainGUI.queue_busy = True
                    self.MainGUI.toggle_buttons()

                if isinstance(queue_item, tuple):
                    queue_item[0](*queue_item[1:])
                elif callable(queue_item):
                    queue_item()
                else:
                    commandList = queue_item
                    for command in commandList:
                        # print 'Processing command: ', command
                        server = command[0]
                        cmd = command[1]

                        if self.abortProcess:
                            break

                        try:
                            # ADX
                            if server == 'A':
                                # print 'In ADX processing section of controlthread'
                                self.queueAdxCommandAndGetAnswer(command)

                        except (CommException, queue.Empty):
                            self.abort()
                            break

                controlQueue.task_done()

                if self.abortProcess:
                    self.cleanUpAfterAbort()

    def _waitForThread(self, serv):

        if serv == 'A':
            while self.adxReady is False:
                pass

    def cleanUpAfterAbort(self):
        """Clear queue and reset threads."""

        self.abortProcess = False

        controlQueueEmpty = controlQueue.empty()

        while controlQueueEmpty is False:
            try:
                tst = controlQueue.get(timeout=3)
                print('Cleaned', tst)
                controlQueue.task_done()
                controlQueueEmpty = controlQueue.empty()
            except queue.Empty:
                controlQueueEmpty = True

    def setupSpecExposureCommands(self, command):
        param = command[1].split()[1].split(',')
        Filename = param[0]
        ExposureTime = param[1]
        NoOfFrames = param[2]
        Directory = param[3]
        NewDark = param[4]

        newfile = 'newfile ' + str(Filename)
        dark = 'dark ' + str(ExposureTime)
        expose = 'rgseries ' + str(NoOfFrames) + ' ' + str(ExposureTime)

        commands = []

        if self.oldFilename != str(Filename) or self.oldDirectory!=str(Directory):
            commands.append(newfile)
            self.oldFilename = str(Filename)
            self.oldDirectory = str(Directory)
            # commands.append('p2dir')  # Arthur's macro to notify detectors

        if NewDark == '1':
            commands.append(dark)

        commands.append(expose)

        # print commands

        return commands

    def setupSpecMkdirCommands(self, command):

        commands = []

        for item in command[1].split(','):
            com = item.split()[0]
            Directory=item.split()[1]
            # print 'Directory to make is: %s' %(Directory)


            newdir = 'u mkdir ' + str(Directory)
            chgdir = 'cd ' +str(Directory)

            commands.append(newdir)
            commands.append(chgdir)
            if com == 'MKDIR':
                commands.append('p2dir')

        return commands

    def setupSpecLogCommands(self, command):

        commands = []

        command=command[1].lstrip('LOGFILE ')
        fname, log = command.split(',')

        new_command = 'fprintf("%s", "%s")' %(str(fname), str(log))
        new_command = str(new_command)

        new_command2 = 'close("%s")' %(str(fname))
        new_command2 = str(new_command2)

        commands.append(new_command)
        commands.append(new_command2)
        return commands

    def queueCommandAndGetAnswer(self, command):

        if command[1] == 'RUN C:\looptest2.hso' or command[1] == 'HOME' or command[1] == '\x1a':
            timeout = 300
        else:
            timeout = 30

        soloSoftCommandQueue.put(command)
        answer = soloSoftAnswerQueue.get(timeout = timeout)
        soloSoftAnswerQueue.task_done()

        print(answer)

        if answer == None or answer[1] == None:
            raise CommException('None was returned in queueCommandAndGetAnswer on ' + str(command))

        elif answer[1] == '0301 Robot Not Homed':
            # wx.CallAfter(self.GUIFrame.OnSafetyButtonPressed, answer)
            self.abort()
        elif answer[1] == '0334 E-Stop':
            # wx.CallAfter(self.GUIFrame.OnSafetyButtonPressed, answer)
            self.abort()
        elif answer[0] == 'STATUS' and answer[1] == '0':
            # wx.CallAfter(self.GUIFrame.OnSafetyButtonPressed, answer)
            self.abort()
        elif len(answer[1].split())>1:
            if answer[1].split()[0] == '0316':
                # wx.CallAfter(self.GUIFrame.OnSafetyButtonPressed, answer)
                self.abort()
        return answer

    def queueAdxCommandAndGetAnswer(self, command):
        if command[1].split()[0] == 'SNAPOFF':
            adxCommandQueue.put(['shutter 0\neoc\n\0'])
        elif command[1].split()[0] == 'SNAP':
            adxCommandQueue.put(['shutter 1\neoc\n\0'])

        elif command[1].split()[0] == 'EXPOSE':
            commands = self.setupSpecExposureCommands(command)
            adxCommandQueue.put(commands)
        elif command[1].split()[0].startswith('MKDIR'):
            # print 'Making new directory'
            commands = self.setupSpecMkdirCommands(command)
            adxCommandQueue.put(commands)
        elif command[1].split()[0].startswith('LOGFILE'):
            print('writing log file via spec')
            # print command
            if self.ADXComm.isSpec:
                commands = self.setupSpecLogCommands(command)

            # print commands
            adxCommandQueue.put(commands)
        else:
            adxCommandQueue.put([command[1]])

    def waitFor(self, state):
        solostate = None

        while(solostate != state and self.abortProcess == False):
            time.sleep(1)
            answer = self.queueCommandAndGetAnswer(('S', 'GETSTATUS'))
            solostate = answer[1]

            if answer == None:
                raise CommException('Recieved None in WaitFor function')

    def abort(self):

        if self.busy:
            self.abortProcess = True

        else:
            self.ADXComm.abort()
            self.cleanUpAfterAbort()


if __name__ == "__main__":

    print("Entering Main!")

    if len(sys.argv) > 1:
        commandFile = sys.argv[1]
        commandList = parseCommandFile(commandFile)
    else:
        commandList = []

    while(1):
        if commandList:
            for command in commandList:

                server = command[0]
                cmd = command[1]
                time.sleep(0.3)

                if server == 'S':

                    if cmd == 'LOOPSTART':
                        loopStartIdx = commandList.index(command)
                    elif cmd == 'LOOPEND':
                        loopEndIdx = commandList.index(command)
                    else:
                        soloSoftCommandQueue.put(command)
                        answer = soloSoftAnswerQueue.get()
                        soloSoftAnswerQueue.task_done()
                        print('Answer :', answer)

                elif server == 'R':
                    soloSoftCommandQueue.put(command)
                    answer = soloSoftAnswerQueue.get()
                    soloSoftAnswerQueue.task_done()
                    print('Answer :', answer)

            if commandList[-1][1] == 'LOOPEND':
                commandList = commandList[loopStartIdx:loopEndIdx+1]
            else:
                commandList = []
            print(' ')

        else:
            inp = input('Write command: ')
            if inp.upper() == 'EXIT':
                break
            try:
                if inp.split()[0] == 'R':
                    serv = inp.split()[0]
                    cmd = inp[2:]
                    soloSoftCommandQueue.put((serv, cmd))
                    answer = soloSoftAnswerQueue.get()
                    soloSoftAnswerQueue.task_done()
                    print('Answer: ', answer)

                elif inp.split()[0] == 'B':
                    auroraCommandQueue.put([('B', inp[2:])])

            except IndexError:
                print('Command not in the right format!')
