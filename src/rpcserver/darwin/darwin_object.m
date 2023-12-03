#include "darwin.h"
#include "../common.h"
#include <objc/objc.h>
#include <objc/runtime.h>
#include <Foundation/Foundation.h>

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
    TRACE("Entered showobject");
    TRACE("Calling objc_show_object with %p", cmd->address);

    Rpc__Response response = RPC__RESPONSE__INIT;
    Rpc__ResponseShowObject resp_show_object = RPC__RESPONSE_SHOW_OBJECT__INIT;
    response.type_case = RPC__RESPONSE__TYPE_SHOW_OBJECT;

    NSString *response_str = getObjectStr((id) cmd->address);

    TRACE("Sending response");
    resp_show_object.description = (char *) [response_str UTF8String];
    response.show_object = &resp_show_object;

    send_response(sockfd, &response);
    TRACE("Sent response");
    return RPC_SUCCESS;

    error:
    TRACE("Failed to show object");
    return RPC_FAILURE;
}
