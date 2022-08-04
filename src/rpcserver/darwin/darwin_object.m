#include "darwin.h"
#include "../common.h"
#include <objc/objc.h>
#include <objc/runtime.h>
#include <Foundation/Foundation.h>

static NSDictionary* getObjectData(id objcObject)
{
    Class objcClass = [objcObject class];

    NSDictionary *objectData = @{
        @"protocols": [NSMutableArray new],
        @"ivars": [NSMutableArray new],
        @"properties": [NSMutableArray new],
        @"methods": [NSMutableArray new],
        @"class_name": [NSString stringWithCString:class_getName(objcClass) encoding:NSUTF8StringEncoding],
        @"class_address": [NSNumber numberWithUnsignedLongLong:(uintptr_t)objcClass],
        @"class_super": [NSNumber numberWithLong:(uintptr_t)class_getSuperclass(objcClass)],
    };

    addProtocolsToDictionary(objcClass, objectData);
    addIvarsToDictionary(objcClass, objectData, objcObject);
    addPropertiesToDictionary(objcClass, objectData);
    addMethodsToDictionary(objcClass, objectData);
    return objectData;
}

static NSString* getObjectStr(id object)
{
    NSDictionary *objectData = getObjectData(object);
    return getDictionaryJsonString(objectData);
}

bool handle_showobject(int sockfd)
{
    TRACE("Entered showobject");
    cmd_showobject_t cmd;
    CHECK(recvall(sockfd, (char *)&cmd, sizeof(cmd)));
    TRACE("Calling objc_show_object with %p", cmd.address);
    NSString *response_str = getObjectStr((id)cmd.address);

    TRACE("Sending response");
    size_t response_len = [response_str length];
    const char *response_cstr = [response_str UTF8String];
    CHECK(sendall(sockfd, (char *)&response_len, sizeof(response_len)));
    CHECK(sendall(sockfd, response_cstr, response_len));
    TRACE("Sent response");
    return true;

error:
    TRACE("Failed to show object");
    return false;
}
