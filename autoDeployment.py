#coding:UTF-8

"""
一个基于python的自动化部署程序
@author:yubang
版本：1.0
2015-03-09
"""

"""
系统目录构成说明：
autoDeployment.py 主程序
fsData 文件仓库
version 部署的代码版本列表
patch 补丁包生成目录
log 日记存放目录
temp 临时目录
"""

import os,sys,hashlib,json,re,base64,time

#-------------------------------------------
#配置文件类
#-------------------------------------------
class Config():
    "配置文件类"
    def __init__(self):
        "初始化"
        global log
        self.__log=log
        self.DATA={
            'ignore':[],
            'copy':[],
            'server':{},
            'client':{},
        }
        self.__load()
    def __load(self):
        "尝试加载配置文件"
        global applicationPath
        configFilePath=applicationPath+"/config.cnf"
        if(os.path.exists(configFilePath)):
            fp=open(configFilePath,'r')
            for temp in fp:
                self.__dealConfig(temp)
            fp.close()
    def __dealConfig(self,data):            
        "处理配置"
        data=data.rstrip()
        data=re.sub(r'^[\s]*','',data)
        if(data[0:1]=="["):
            #配置类型改变
            data=re.sub(r'\].*','',data)
            data=data[1:len(data)]
            self.__sign=data
        elif(data[0:1]=="#"):
            #注释行忽略
            pass
        else:
            #配置数据
            self.__setConfig(data)
    def __setConfig(self,data):
        "设置属性"
        if(data==""):
            return None
        if(self.__sign=='ignore'):
            self.DATA['ignore'].append(data)
            self.__log.log(unicode("添加忽略表达式：%s"%(data),"UTF-8"),"temp")
        elif(self.__sign=='copy'):
            self.DATA['copy'].append(data)
            self.__log.log(unicode("添加复制表达式：%s"%(data),"UTF-8"),"temp")                      
    def checkIgnore(self,path):
        "检测路径是不是匹配忽略列表"
        for el in self.DATA['ignore']:
            if(re.match(el,path)!=None):
                return True
        return False
        
#--------------------------------------------
#工具类
#--------------------------------------------
class Tools():
    "工具类"
    def __init__(self):
        global log
        self.__log=log
    def removeFileOrDir(self,path):
        "删除文件或递归删除文件夹"
        result=True
        if(os.path.exists(path)):
            if(os.path.isfile(path)):
                os.remove(path)
            else:
                fps=os.listdir(path)
                for fp in fps:
                    result=self.removeFileOrDir(path+"/"+fp)
                    if(not result):
                        return result
                os.rmdir(path)
        else:
            result=False
        return result
    def copyFileOrDir(self,oldPath,newPath):
        "复制文件或递归复制文件夹"
        result=True
        if(os.path.exists(oldPath)):
            if(os.path.isfile(oldPath)):
                
                #防止父目录不存在
                path=os.path.dirname(newPath)
                if(not os.path.exists(path)):
                    os.makedirs(path)
                #文件复制
                in_fp=open(oldPath,'rb')
                out_fp=open(newPath,'wb')
                out_fp.write(in_fp.read())
                in_fp.close()
                out_fp.close()
                self.__log.log(unicode("文件复制：%s -> %s"%(oldPath,newPath),"UTF-8"),"fileOption")
            else:
                if(not os.path.exists(newPath)):
                    os.makedirs(newPath)
                    self.__log.log(unicode("创建文件夹：%s"%(newPath),"UTF-8"),"fileOption")
                fps=os.listdir(oldPath)
                for fp in fps:
                    result=self.copyFileOrDir(oldPath+"/"+fp,newPath+"/"+fp)
                    if(not result):
                        return result
        else:
            result=False
        return result
    def copyFromEl(self,oldPath,newPath,key=".",el=None):
        "根据规则复制"
        result=None
        if(not os.path.exists(oldPath)):
            result=False
        else:
            result=True
            if(os.path.isfile(oldPath)):
                for t in el:
                    if(re.match(t,key)!=None):
                        #启用复制
                        self.copyFileOrDir(oldPath,newPath)
                        self.__log.log(unicode("文件覆盖：%s -> %s"%(oldPath,newPath),"UTF-8"),"fileOption")
                        break            
            else:
                fps=os.listdir(oldPath)
                for fp in fps:
                    self.copyFromEl(oldPath+"/"+fp,newPath+"/"+fp,key+"/"+fp,el)
                    if(not os.path.exists(newPath)):
                        os.makedirs(newPath)
        return result            

#--------------------------------------------
#文件列表转md5列表
#--------------------------------------------
class FsToDataSystem():
    "文件列表转md5列表处理类"
    def __init__(self):
        global config,log
        self.__config=config
        self.__log=log
    def getMd5Lists(self,path,key='.',lists=None):
        "获取一个文件夹的所有md5列表"
        
        if(lists==None):
            lists={}
        if(not os.path.exists(path)):
            print unicode("文件(%s)不存在!"%(path),"UTF-8")
            return lists
        if(os.path.isdir(path)):
            fps=os.listdir(path)
            for fp in fps:
                lists=self.getMd5Lists(path+"/"+fp,key+"/"+fp,lists)
            if(self.__config.checkIgnore(key)):
                self.__log.log(unicode("忽略文件：%s"%(path),"UTF-8"),'getMd5')
            else:
                lists[key]="#"
        else:
            if(self.__config.checkIgnore(key)):
                self.__log.log(unicode("忽略文件：%s"%(path),"UTF-8"),'getMd5')
            else:
                fp=open(path,'rb')
                md5=hashlib.md5(fp.read()).hexdigest()
                fp.close()
                lists[key]=md5
        return lists        


#--------------------------------------------
#补丁包生成类
#--------------------------------------------
class PatchSystem():
    "补丁包生成类"
    def __init__(self):
        pass
    def __getAddFile(self,lists,path,path2):
        "提取新增加的文件"
        global applicationPath
        dirPath=applicationPath+"/patch/patch/data/"
        os.makedirs(dirPath)
        tools=Tools()
        for temp in lists:
            texts=temp.split("|")
            if(texts[2]=="add" and texts[1]!="#"):
                filePath=path2+"/"+base64.b64decode(texts[0])
                targetDirPath=dirPath+texts[1][0:8]+"/"+texts[1][8:16]+"/"+texts[1][16:24]
                if(not os.path.exists(targetDirPath)):
                    os.makedirs(targetDirPath)
                tools.copyFileOrDir(filePath,targetDirPath+"/"+texts[1][24:32])
                
    def getDifferentList(self,newLists,oldList):
        "获取差异列表"
        result=[]
        result=self.__checkDifferent(newLists,oldList,result,"add")
        result=self.__checkDifferent(oldList,newLists,result,"delete")
        return result
                
    def __checkDifferent(self,a,b,lists,status):
        "生成补丁包差异列表"
        for t1 in a:
            sign=False
            for t2 in b:
                if(t1==t2):
                    #检测到key一致
                    if(a[t1]!=b[t2]):
                        "文件修改过"
                        sign=True
                        if(status=='add'):
                            lists.append("%s|%s|%s"%(base64.b64encode(t1),a[t1],'update'))
                        break
            if(not sign):
                lists.append("%s|%s|%s"%(base64.b64encode(t1),a[t1],status))
        return lists
    def buildPatch(self,newLists,oldList,path,path2):
        "生成补丁包"
        if(os.path.exists(path)):
            print unicode("补丁包目录(%s)已经存在，中断操作！"%(path),"UTF-8")
            return False
        else:
            os.makedirs(path)
            result=[]
            result=self.__checkDifferent(newLists,oldList,result,"add")
            result=self.__checkDifferent(oldList,newLists,result,"delete")
            #写入修改文件列表
            fp=open(path+"/update",'w')
            fp.write(json.dumps(result))
            fp.close()
            #写入标准文件列表
            fp=open(path+"/new",'w')
            fp.write(json.dumps(newLists))
            fp.close()
            
            self.__getAddFile(result,path,path2)
            return True
            
#--------------------------------------------
#部署文件一致性检测
#--------------------------------------------        
class FsCheckSystem():
    "部署文件一致性检测类"
    def __init__(self):
        pass
    def check(self,updateList):
        "检测是否可以部署"
        result=True
        fsSaveGetSystem=FsSaveGetSystem()
        for temp in updateList:
            t=temp.split("|")
            if(t[2]=='add' or t[2]=='update'):
                if(not fsSaveGetSystem.checkFile(t[1])):
                    print unicode("缺失文件：%s（md5：%s）"%(base64.b64decode(t[0]),t[1].encode("UTF-8")),"UTF-8")
                    result=False
        return result
        
#--------------------------------------------
#文件仓库存储系统
#--------------------------------------------    
class FsSaveGetSystem():
    "文件仓库存储系统类"
    def __init__(self):
        self.__tools=Tools()
    def addNewFile(self,filePath,path="."):
        "添加新文件到文件仓库"
        global applicationPath
        if(os.path.isdir(filePath)):
            if(not os.path.exists(applicationPath+"/fsData/"+path)):
                os.makedirs(applicationPath+"/fsData/"+path)
            fps=os.listdir(filePath)
            for fp in fps:
                self.addNewFile(filePath+"/"+fp,path+"/"+fp)
        else:
            if(not os.path.exists(applicationPath+"/fsData/"+path)):
                self.__tools.copyFileOrDir(filePath,applicationPath+"/fsData/"+path)
            else:
                print unicode("忽略文件：%s"%(path),"UTF-8")
    def getFile(self,md5):
        "获取特定md5的数据流"
        global applicationPath
        path=applicationPath+"/fsData/"+md5[0:8]+"/"+md5[8:16]+"/"+md5[16:24]+"/"+md5[24:32]
        if(os.path.exists(path)):
            fp=open(path,'rb')
            text=fp.read()
            fp.close()
            return True,text
        else:
            return False,None            
    def checkFile(self,md5):
        "检测文件是否存在"
        if(md5=="#"):
            return True
        global applicationPath
        path=applicationPath+"/fsData/"+md5[0:8]+"/"+md5[8:16]+"/"+md5[16:24]+"/"+md5[24:32]
        if(os.path.exists(path)):
            return True
        else:
            return False    
        
#--------------------------------------------
#日记系统
#--------------------------------------------
class LogSystem():
    "日记系统" 
    def __init__(self):
        global applicationPath
        self.__path=applicationPath+"/log/"+time.strftime("%Y%m%d")
        self.__createDir()
        self.__loginLog()
    def __createDir(self):
        "创建文件夹"
        if(not os.path.exists(self.__path)):
            os.makedirs(self.__path)
    def __loginLog(self):
        "向日记写入空行"
        self.log("\n\n","option")
        self.log("\n\n","fileOption")
    def log(self,message,logType):
        "记录日记"
        print message
        if(type(message).__name__=="unicode"):
            message=message.encode("UTF-8")
        fp=open(self.__path+"/"+logType+".log",'a')
        fp.write(message)
        fp.write("\n")
        fp.close()
        
        
#--------------------------------------------
#代码部署系统
#--------------------------------------------
class CodeManagerSystem():
    "代码部署系统" 
    def __init__(self):
        pass
        
        
#--------------------------------------------
#自动化系统核心类
#--------------------------------------------
class Core():
    "自动化系统核心类"
    def __init__(self):
        self.__createDir()
        global log
        self.__log=log
        self.__tools=Tools()
    def __del__(self):
        self.__deleteTempDirFile()
        
    def __createDir(self):
        "创建程序所需的文件夹"
        global applicationPath 
        fps=['log','version','fsData','temp','patch','temp/patch']
        for temp in fps:
            dirPath=applicationPath+"/"+temp
            if(not os.path.exists(dirPath)):
                os.makedirs(dirPath)
                
    def __deleteTempDirFile(self,tempDirPath=None):
        "删除临时目录内容"
        return None
        if(tempDirPath==None):
            global applicationPath
            tempDirPath=applicationPath+"/temp"
        if(os.path.exists(tempDirPath) and os.path.isdir(tempDirPath)):
            fps=os.listdir(tempDirPath)
            for fp in fps:
                tempPath=tempDirPath+"/"+fp
                if(os.path.isdir(tempPath)):
                    self.__deleteTempDirFile(tempPath)
                    #print unicode("删除文件夹","UTF-8"),tempPath
                    os.rmdir(tempPath)
                else:
                    print unicode("删除文件","UTF-8"),tempPath
                    os.remove(tempPath)
                    
    def __list(self):
        "获取文件md5列表"
        global applicationPath
        dao=FsToDataSystem()
        lists=dao.getMd5Lists(sys.argv[2])
        text=json.dumps(lists)
        fp=open(applicationPath+'/patch/md5List.txt','w')
        fp.write(text)
        fp.close()
        print unicode("md5文件列表建立完成！","UTF-8")
        print unicode("文件列表输出于：","UTF-8"),applicationPath+"/patch/md5List.txt"
        
    def __patch(self):
        "生成补丁包"
        global applicationPath
        if(not os.path.exists(sys.argv[2])):
            self.__log.log(unicode("文件（%s）不存在！"%(sys.argv[2]),"UTF-8"),"option")
            return None
        elif(not os.path.exists(sys.argv[3])):
            self.__log.log(unicode("文件（%s）不存在！"%(sys.argv[3]),"UTF-8"),"option")
            return None
        else:
            dao=FsToDataSystem()
            #新版md5列表
            if(os.path.isdir(sys.argv[2])):
                lists1=dao.getMd5Lists(sys.argv[2])
            else:
                fp=open(sys.argv[2],'r')
                lists1=json.loads(fp.read())
                fp.close()
            #旧版md5列表
            if(os.path.isdir(sys.argv[3])):
                lists2=dao.getMd5Lists(sys.argv[3])
            else:
                fp=open(sys.argv[3],'r')
                lists2=json.loads(fp.read())
                fp.close()
            
            patchSystem=PatchSystem()
            result=patchSystem.buildPatch(lists1,lists2,applicationPath+"/patch/patch",sys.argv[2])
            if(result):
                self.__log.log(unicode("生成补丁包完成，补丁包(文件夹)输出于：%s"%(applicationPath+"/patch/patch"),"UTF-8"),"option")
    
    def __commit(self):
        "提交一个补丁包"
        global applicationPath
        v=0
        while True:
            targetPath=applicationPath+"/version/"+str(v)
            if(not os.path.exists(targetPath)):
                break
            v=v+1
        os.makedirs(targetPath)
        
        if(not os.path.exists(sys.argv[2])):
            self.__log.log(unicode("补丁包（%s）不存在"%(sys.argv[2]),"UTF-8"),"option")
            return None
        
        
        self.__tools.copyFileOrDir(sys.argv[2]+"/new",targetPath+"/new")
        self.__tools.copyFileOrDir(sys.argv[2]+"/update",targetPath+"/update")
        
        #文件仓库加入新增文件
        fsSaveGetSystem=FsSaveGetSystem()
        fsSaveGetSystem.addNewFile(sys.argv[2]+"/data")
        self.__log.log(unicode("成功处理补丁包，当前版本号：%d"%(v),"UTF-8"),"option")
    
    def __release(self):
        "显示当前的提交的版本列表"
        global applicationPath
        fps=os.listdir(applicationPath+"/version")
        for temp in fps:
            print unicode("提交的版本号：%s(提交时间:%s)"%(temp,time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(os.path.getmtime(applicationPath+"/version/"+temp)))),"UTF-8")
    
    def __deploy(self,version,target):
        "部署代码"
        global applicationPath
        
        #提取版本列表
        path=applicationPath+"/version/"+version+"/new"
        if(os.path.exists(path)):
            #新版
            fp=open(path,'r')
            lists=json.loads(fp.read())
            fp.close()
            #旧版
            dao=FsToDataSystem()
            oldLists=dao.getMd5Lists(target)
            
            #获取升级列表
            dao=PatchSystem()
            updateList=dao.getDifferentList(lists,oldLists)
            
            
            #检测新版是否可以部署（文件完整性）
            fsCheckSystem=FsCheckSystem()
            if(fsCheckSystem.check(updateList)):
                
                #备份代码，防止出错的时候可以回滚
                tools=Tools()
                tools.removeFileOrDir(applicationPath+"/temp/backup")
                tools.copyFileOrDir(sys.argv[3],applicationPath+"/temp/backup")
        
                
                tools=Tools()
                fsSaveGetSystem=FsSaveGetSystem()
                for command in updateList:
                    texts=command.split("|")
                    if(texts[2]=="add" or texts[2]=="update"):
                        fpPath=target+"/"+base64.b64decode(texts[0])
                        if(texts[1]=="#"):
                            #文件夹
                            if(not os.path.exists(fpPath)):
                                os.makedirs(fpPath)
                        else:
                            #文件
                            result,text=fsSaveGetSystem.getFile(texts[1])
                            if(result):
                                dirPath=os.path.dirname(fpPath)
                                if(not os.path.exists(dirPath)):
                                    os.makedirs(dirPath)
                                fp=open(fpPath,'wb')
                                fp.write(text)
                                fp.close()
                    elif(texts[2]=="delete"):
                        if(base64.b64decode(texts[0])!="."):
                            tools.removeFileOrDir(target+"/"+base64.b64decode(texts[0]))
            else:
                self.__log.log(unicode("由于缺失文件，部署终止！","UTF-8"),"option")
                return -2
            
        else:
            self.__log.log(unicode("该版本（%s）不存在"%(version),"UTF-8"),"option")
            return -1
        
        #根据规则提取旧文件覆盖
        global config
        tools.copyFromEl(applicationPath+"/temp/backup",target,".",config.DATA['copy'])
        
        #部署阶段完成，等待用户确认
        self.__log.log(unicode("代码部署完成，请检查部署情况，如果需要回退请按R或r，其它则不回退！","UTF-8"),"option")
        ch=raw_input(unicode("请输入：","UTF-8").encode("UTF-8"))
        if(ch=='r' or ch == 'R'):
            if(tools.removeFileOrDir(target) and tools.copyFileOrDir(applicationPath+"/temp/backup",target)):
                tools.removeFileOrDir(applicationPath+"/temp/backup")
                self.__log.log(unicode("回退成功！","UTF-8"),"option")
            else:
                self.__log.log(unicode("回退失败","UTF-8"),"option")
        else:
            self.__log.log(unicode("部署成功！","UTF-8"),"option")
                
    def init(self):
        "入口函数处理命令行参数"
        if(len(sys.argv)==1):
            print unicode("具体用法请查看API文档","UTF-8")
        else:
            if(sys.argv[1]=='--list'):
                "获取文件md5列表"
                self.__log.log(unicode("获取文件md5列表","UTF-8"),"option")
                self.__list()
            elif(sys.argv[1]=='--patch'):
                "生成补丁包"
                self.__log.log(unicode("生成补丁包","UTF-8"),"option")
                self.__patch()
            elif(sys.argv[1]=='--commit'):
                "提交一个补丁包"
                self.__log.log(unicode("提交补丁包","UTF-8"),"option")
                self.__commit()        
            elif(sys.argv[1]=='--release'):
                "显示提交的版本列表"
                self.__release()
            elif(sys.argv[1]=='--deploy'):
                "部署代码"
                self.__log.log(unicode("部署代码","UTF-8"),"option")
                self.__deploy(sys.argv[2],sys.argv[3])

                                   
applicationPath=os.path.dirname(os.path.realpath(__file__))
log=LogSystem()
config=Config()


if __name__ == "__main__":
    core=Core()
    core.init()
