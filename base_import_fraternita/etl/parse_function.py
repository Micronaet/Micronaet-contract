# -*- encoding: utf-8 -*-
# Funzioni utilizzate per l'import:
tipo_cdc= {1: "Letture",
           2: "Postalizzazione",
           5: "Segnaletica",
           10: "Cartografia e rilievi",
           11: "Ins. dati",
           20: "Infor. territ.",
           35: "Falegnameria",
           40: "Generale",
           50: "Logistica",
           60: "Acqua",
           80: "Letture Italia",
          }

def crea_department(sock, dbname, uid, pwd, item):
    ''' Creo department con numero    
    '''
    #'name': 'Management', 'complete_name': 'Management', 'manager_id': [2, 'Fabien Pinckaer]
    
    item=int(item)
    if item in tipo_cdc:
       item_mod = sock.execute(dbname, uid, pwd, 'hr.department', 'search', [('name','=',tipo_cdc[item])])
       if item_mod: # exist
          return item_mod[0]
       else: # create
          return sock.execute(dbname, uid, pwd, 'hr.department', 'create', {'name': tipo_cdc[item],
                                                                            'manager_id': 1, # TODO mettere quello corretto
                                                                           })
    return False         

def get_department(sock, dbname, uid, pwd, id_ref):
    # Return ID with ref external
    if id_ref in tipo_cdc:
       return crea_department(sock, dbname, uid, pwd, id_ref)
    return False

def prepare_date_xls(valore):
    ''' Calcolo data di Excel (giorno 1= 01/01/1900)
    ''' 
    from datetime import datetime 
    from datetime import timedelta
    
    if type(valore) not in (type(0), type(0.0)): # is int or float
       return False
    return (datetime.strptime("1900-01-01",'%Y-%m-%d') + timedelta(days = valore - 2)).strftime('%Y-%m-%d')

def prepare_date_gg_mm_aaaa(valore):
    ''' Calcolo data (formato 01/01/1900)
    ''' 
    if valore and len(valore)==10:
       return "%s-%s-%s"%(valore[-4:],valore[3:5],valore[:2])
    return False   

def prepare_date_aaaa_mm_gg(valore):
    ''' Calcolo data (formato 1900/01/01)
    ''' 
    if valore and len(valore)==10:
       return "%s-%s-%s"%(valore[:4],valore[5:7],valore[-2:])
    return False   

def prepare_date_ISO(valore):
    ''' Calcolo data (formato 1900/01/01)
    ''' 
    valore=valore.strip()
    if valore and len(valore)==8:
       return "%s-%s-%s"%(valore[:4],valore[4:6],valore[-2:])
    return False   

def prepare_float(valore):
    ''' Calcolo float
    '''
    try:
        if valore:
           valore=valore.strip().replace(",",".")
           return float(valore)
    except:
        pass
    return 0.0

def getItalian(sock, dbname, uid, pwd, name):
    # get Language if exist (use english name request 
    return sock.execute(dbname, uid, pwd, 'res.lang', 'search', [('name', '=', name),])[0]

def getPartner(sock, dbname, uid, pwd, ref):
    # get Language if exist (use english name request 
    item=sock.execute(dbname, uid, pwd, 'res.partner', 'search', [('ref', '=', ref),('import','=',True)])
    if item:
       return item[0]
    else:
       print "[ERR] Partner non trovato:", ref   
       return False   

def getPartner_not_employee(sock, dbname, uid, pwd, ref):
    # get Language if exist (use english name request 
    item=sock.execute(dbname, uid, pwd, 'res.partner', 'search', [('ref', '=', ref),('import','=',True),('is_employee','=',False)])
    if item:
       return item[0]
    else:
       print "[ERR] Partner non trovato:", ref   
       return False   
    
def prepare(valore):  
    # For problems: input win output ubuntu; trim extra spaces
    #valore=valore.decode('ISO-8859-1')
    valore=valore.decode('cp1252')
    valore=valore.encode('utf-8')
    return valore.strip()

def prepare_telephone(valore):
    valore=valore.strip()
    valore=valore.replace("-","/").replace("_","/").replace(" ","").replace(".","/").replace("//","/")
    return valore
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
