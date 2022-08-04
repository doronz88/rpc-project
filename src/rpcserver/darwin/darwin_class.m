#include "darwin.h"
#include "../common.h"
#include <objc/objc.h>
#include <objc/runtime.h>
#include <Foundation/Foundation.h>

static NSDictionary* getClassDescription(Class objcClass)
{
    NSDictionary *classDescription = @{                          
        @"protocols": [NSMutableArray new],
        @"ivars": [NSMutableArray new],
        @"properties": [NSMutableArray new],
        @"methods": [NSMutableArray new],
        @"name": [NSString stringWithCString:class_getName(objcClass) encoding:NSUTF8StringEncoding],
        @"address": [NSNumber numberWithLong:(uintptr_t)objcClass],
        @"super": [NSNumber numberWithLong:(uintptr_t)class_getSuperclass(objcClass)],
    };

    addProtocolsToDictionary(objcClass, classDescription);
    addIvarsToDictionary(objcClass, classDescription, nil);
    addPropertiesToDictionary(objcClass, classDescription);
    addMethodsToDictionary(objcClass, classDescription);

    return classDescription;
}

static NSString* getClassDescriptionStr(Class objcClass)
{
    NSDictionary *classDescription = getClassDescription(objcClass);
    return getDictionaryJsonString(classDescription);
}

int handle_showclass(int sockfd)
{
    TRACE("Entered showclass");
    cmd_showclass_t cmd;
    CHECK(recvall(sockfd, (char *)&cmd, sizeof(cmd)));
    NSString *response_str = getClassDescriptionStr((id)cmd.address);

    TRACE("Sending response");
    size_t response_len = [response_str length];
    const char *response_cstr = [response_str UTF8String];
    CHECK(sendall(sockfd, (char *)&response_len, sizeof(response_len)));
    CHECK(sendall(sockfd, response_cstr, response_len));
    TRACE("Sent response");
    return 0;

error:
    TRACE("Failed to show class");
    return -1;
}
