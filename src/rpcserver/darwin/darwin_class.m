#include "darwin.h"
#include "../common.h"
#include <objc/objc.h>
#include <objc/runtime.h>
#include <Foundation/Foundation.h>

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
    Rpc__Response response = RPC__RESPONSE__INIT;
    Rpc__ResponseShowClass resp_show_class = RPC__RESPONSE_SHOW_CLASS__INIT;
    response.type_case = RPC__RESPONSE__TYPE_SHOW_CLASS;

    NSString *response_str = getClassDescriptionStr((id) cmd->address);
    resp_show_class.description = (char *) [response_str UTF8String];
    response.show_class = &resp_show_class;

    TRACE("Sending response");
    send_response(sockfd, &response);
    TRACE("Sent response");
    return RPC_SUCCESS;

    error:
    TRACE("Failed to show class");
    return RPC_FAILURE;
}
