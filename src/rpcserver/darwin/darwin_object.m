#include "../common.h"
#include "darwin.h"
#include <Foundation/Foundation.h>
#include <objc/objc.h>
#include <objc/runtime.h>

static NSDictionary *getObjectData(id objcObject) {
  Class objcClass = [objcObject class];

  NSDictionary *objectData = @{
    @"protocols": [NSMutableArray new],
    @"ivars": [NSMutableArray new],
    @"properties": [NSMutableArray new],
    @"methods": [NSMutableArray new],
    @"class_name": [NSString stringWithCString:class_getName(objcClass) encoding:NSUTF8StringEncoding],
    @"class_address": [NSNumber numberWithUnsignedLongLong:(uintptr_t) objcClass],
    @"class_super": [NSNumber numberWithLong:(uintptr_t) class_getSuperclass(objcClass)],
  };

  addProtocolsToDictionary(objcClass, objectData);
  addIvarsToDictionary(objcClass, objectData, objcObject);
  addPropertiesToDictionary(objcClass, objectData);
  addMethodsToDictionary(objcClass, objectData);
  return objectData;
}

static NSString *getObjectStr(id object) {
  NSDictionary *objectData = getObjectData(object);
  return getDictionaryJsonString(objectData);
}

bool handle_showobject(int sockfd, Rpc__CmdShowObject *cmd) {
  TRACE("Calling objc_show_object with %p", cmd->address);
  Rpc__ResponseShowObject resp_show_object = RPC__RESPONSE_SHOW_OBJECT__INIT;
  NSString *response_str = getObjectStr((id) cmd->address);

  resp_show_object.description = (char *) [response_str UTF8String];

  return send_response(sockfd, (ProtobufCMessage *) &resp_show_object);
}
