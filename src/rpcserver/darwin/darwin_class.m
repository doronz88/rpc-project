#include "../common.h"
#include "darwin.h"
#include <Foundation/Foundation.h>
#include <objc/objc.h>
#include <objc/runtime.h>

static NSDictionary *getClassDescription(Class objcClass) {
  NSDictionary *classDescription = @{
    @"protocols": [NSMutableArray new],
    @"ivars": [NSMutableArray new],
    @"properties": [NSMutableArray new],
    @"methods": [NSMutableArray new],
    @"name": [NSString stringWithCString:class_getName(objcClass) encoding:NSUTF8StringEncoding],
    @"address": [NSNumber numberWithLong:(uintptr_t) objcClass],
    @"super": [NSNumber numberWithLong:(uintptr_t) class_getSuperclass(objcClass)],
  };

  addProtocolsToDictionary(objcClass, classDescription);
  addIvarsToDictionary(objcClass, classDescription, nil);
  addPropertiesToDictionary(objcClass, classDescription);
  addMethodsToDictionary(objcClass, classDescription);

  return classDescription;
}

static NSString *getClassDescriptionStr(Class objcClass) {
  NSDictionary *classDescription = getClassDescription(objcClass);
  return getDictionaryJsonString(classDescription);
}

int handle_showclass(int sockfd, Rpc__CmdShowClass *cmd) {
  TRACE("Entered showclass");
  Rpc__ResponseShowClass resp_show_class = RPC__RESPONSE_SHOW_CLASS__INIT;

  NSString *response_str = getClassDescriptionStr((id) cmd->address);
  resp_show_class.description = (char *) [response_str UTF8String];

  return send_response(sockfd, (ProtobufCMessage *) &resp_show_class);
}
