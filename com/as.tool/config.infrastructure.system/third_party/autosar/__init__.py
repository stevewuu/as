from autosar.workspace import Workspace
import autosar.component
import autosar.behavior
import autosar.portinterface
import autosar.datatype
import autosar.constant
import autosar.signal
import autosar.package
import autosar.rte
from abc import (ABC,abstractmethod)
from autosar.base import splitRef
import autosar.bsw.com
import autosar.bsw.os

import ntpath
import os
import xml.etree.ElementTree as ElementTree

def workspace(version=3.0, patch = 2, schema=None, attributes=None, useDefaultWriters=True):
   if schema is None and ( (version == 3.0 and patch == 2) or (version == "3.0.2") ):
      schema = 'autosar_302_ext.xsd'
   return autosar.Workspace(version, patch, schema, attributes, useDefaultWriters)


   

def splitRef(ref):
   return autosar.base.splitRef(ref)

def DataElement(name, typeRef, isQueued=False, softwareAddressMethodRef=None, swCalibrationAccess=None, swImplPolicy = None, parent=None, adminData=None):
   return autosar.portinterface.DataElement(name, typeRef, isQueued, softwareAddressMethodRef, swCalibrationAccess, swImplPolicy, parent, adminData)

def ApplicationError(name, errorCode, parent=None, adminData=None):
   return autosar.portinterface.ApplicationError(name, errorCode, parent, adminData)

def ModeGroup(name, typeRef, parent=None, adminData=None):
   return autosar.portinterface.ModeGroup(name, typeRef, parent, adminData)

def CompuMethodConst(name, elements, parent=None, adminData=None):
   return autosar.datatype.CompuMethodConst(name, elements, parent, adminData)

def Parameter(name, typeRef, swAddressMethodRef=None, swCalibrationAccess=None, parent=None, adminData=None):
   return autosar.portinterface.Parameter(name, typeRef, swAddressMethodRef, swCalibrationAccess, parent, adminData)


#template support
class Template(ABC):
   
   usageCount = 0 #number of times this template have been applied
   
   @classmethod
   def get(cls, ws):
      ref = cls.ref(ws)
      if ws.find(ref) is None:
         ws.apply(cls)
      return ws.find(ref)
   
   @classmethod
   @abstractmethod
   def apply(cls, ws, **kwargs):
      """
      Applies this class template to the workspace ws
      """

#### Constant Helpers ####
def createConstantTemplateFromEnumerationType(name, dataTypeTemplate):
   @classmethod
   def apply(cls, ws):
      package = ws.getConstantPackage()
      if package.find(cls.__name__) is None:
         ws.apply(cls.dataTypeTemplate)
         package.createConstant(cls.__name__, cls.dataTypeTemplate.__name__, len(cls.dataTypeTemplate.valueTable)-1)
   return type(name, (autosar.Template,), dict(dataTypeTemplate=dataTypeTemplate, apply=apply))

def createConstantTemplateFromPhysicalType(name, dataTypeTemplate):
   @classmethod
   def apply(cls, ws):
      package = ws.getConstantPackage()
      if package.find(cls.__name__) is None:
         ws.apply(cls.dataTypeTemplate)
         package.createConstant(cls.__name__, cls.dataTypeTemplate.__name__, cls.dataTypeTemplate.maxValue)
   return type(name, (autosar.Template,), dict(dataTypeTemplate=dataTypeTemplate, apply=apply))
#### Port Interface Helpers ####
def createSenderReceiverInterfaceTemplate(name, dataTypeTemplate):
   @classmethod
   def apply(cls, ws):
      package = ws.getPortInterfacePackage()
      if package.find(name) is None:
         ws.apply(cls.dataTypeTemplate)
         package.createSenderReceiverInterface(name, autosar.DataElement(name, cls.dataTypeTemplate.__name__))
   return type(name, (autosar.Template,), dict(dataTypeTemplate=dataTypeTemplate, apply=apply))
#### Signal Helpers ####
def _createProvidePortHelper(swc, name, portInterfaceTemplate, initValueTemplate=None):
   ws = swc.rootWS()
   ws.apply(portInterfaceTemplate)
   if initValueTemplate is not None:
      ws.apply(initValueTemplate)
      swc.createProvidePort(name, portInterfaceTemplate.__name__, initValueRef=initValueTemplate.__name__)
   else:
      swc.createProvidePort(name, portInterfaceTemplate.__name__)

def _createRequirePortHelper(swc, name, portInterfaceTemplate, initValueTemplate=None, aliveTimeout=0):
   ws = swc.rootWS()
   ws.apply(portInterfaceTemplate)
   if initValueTemplate is not None:
      ws.apply(initValueTemplate)
      swc.createRequirePort(name, portInterfaceTemplate.__name__, initValueRef=initValueTemplate.__name__, aliveTimeout=aliveTimeout)
   else:
      swc.createRequirePort(name, portInterfaceTemplate.__name__, aliveTimeout=aliveTimeout)

def _createProvidePortTemplate(innerClassName, templateName, portInterfaceTemplate, initValueTemplate):
   @classmethod
   def apply(cls, swc):
      _createProvidePortHelper(swc, cls.name, cls.portInterfaceTemplate, cls.initValueTemplate)
   return type(innerClassName, (autosar.Template,), dict(name=templateName, portInterfaceTemplate=portInterfaceTemplate, initValueTemplate=initValueTemplate, apply=apply))

def _createRequirePortTemplate(innerClassName, templateName, portInterfaceTemplate, initValueTemplate, aliveTimeout=0):
   @classmethod
   def apply(cls, swc):
      _createRequirePortHelper(swc, cls.name, cls.portInterfaceTemplate, cls.initValueTemplate, cls.aliveTimeout)
   return type(innerClassName, (autosar.Template,), dict(name=templateName, portInterfaceTemplate=portInterfaceTemplate, initValueTemplate=initValueTemplate, aliveTimeout=aliveTimeout, apply=apply))
   

def createSenderReceiverPortTemplate(name, portInterfaceTemplate, initValueTemplate=None, aliveTimeout=0):
   return type(name, (), dict(Provide=_createProvidePortTemplate('Provide', name, portInterfaceTemplate, initValueTemplate),
                              Send=_createProvidePortTemplate('Send', name, portInterfaceTemplate, initValueTemplate),
                              Require=_createRequirePortTemplate('Require', name, portInterfaceTemplate, initValueTemplate, aliveTimeout),
                              Receive=_createRequirePortTemplate('Receive', name, portInterfaceTemplate, initValueTemplate, aliveTimeout)))
