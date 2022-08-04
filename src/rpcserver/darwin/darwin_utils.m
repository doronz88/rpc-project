#include <objc/objc.h>
#include <objc/runtime.h>
#include <Foundation/Foundation.h>

void addProtocolsToDictionary(Class objcClass, NSDictionary *outDictionary)
{
    uint outCount = 0;
    id *protocols = class_copyProtocolList(objcClass, &outCount);

    for (uint i = 0; i < outCount; ++i) {
        [outDictionary[@"protocols"] addObject: [NSString stringWithCString:protocol_getName(protocols[i]) encoding:NSUTF8StringEncoding]];
    }
    if (protocols) {
        free(protocols);
    }
}

static void addToIvars(Class objcClass, NSDictionary *outDictionary, id objcObject, Ivar ivar)
{
    NSMutableDictionary *currIvarObject = [NSMutableDictionary new];
    NSString *ivarName = [NSString stringWithCString:ivar_getName(ivar) encoding:NSUTF8StringEncoding];
    [currIvarObject setObject:ivarName forKey:@"name"];
    NSString *ivarType = [NSString stringWithCString:ivar_getTypeEncoding(ivar) encoding:NSUTF8StringEncoding];
    [currIvarObject setObject:ivarType forKey:@"type"];
    NSNumber *ivarOffset = [NSNumber numberWithInt:ivar_getOffset(ivar)];
    [currIvarObject setObject:ivarOffset forKey:@"offset"];

    if (objcObject) {
        id value = [NSNumber numberWithUnsignedLongLong:(uintptr_t)object_getIvar(objcObject, ivar)];
        [currIvarObject setObject:value forKey:@"value"];
    }
    [outDictionary[@"ivars"] addObject:currIvarObject];
}

void addIvarsToDictionary(Class objcClass, NSDictionary *outDictionary, id objcObject)
{
    uint outCount = 0;
    Ivar *ivars = class_copyIvarList(objcClass, &outCount);
    for (uint i = 0; i < outCount; ++i) {
        addToIvars(objcClass, outDictionary, objcObject, ivars[i]);
    }
    if (ivars) {
        free(ivars);
    }

    for (Class superClass = class_getSuperclass(objcClass); superClass; superClass = class_getSuperclass(superClass)) {
        ivars = class_copyIvarList(superClass, &outCount);
        for (size_t i = 0; i < outCount; ++i) {
            addToIvars(objcClass, outDictionary, objcObject, ivars[i]);
        }
        if (ivars) {
            free(ivars);
        }
    }
}

void addPropertiesToDictionary(Class objcClass, NSDictionary *outDictionary)
{
    uint outCount = 0;
    NSMutableArray *fetchedProperties = [NSMutableArray new];
    objc_property_t *properties = class_copyPropertyList(objcClass, &outCount);
    NSString *propertyName;
    for (uint i = 0; i < outCount; ++i) {
        propertyName = [NSString stringWithCString:property_getName(properties[i]) encoding:NSUTF8StringEncoding];
        if ([fetchedProperties containsObject:propertyName]) {
            continue;
        }
        else {
            [fetchedProperties addObject:propertyName];
        }
        [outDictionary[@"properties"] addObject:@{
            @"name": propertyName,
            @"attributes": [NSString stringWithCString:property_getAttributes(properties[i]) encoding:NSUTF8StringEncoding],
        }];
    }
    if (properties) {
        free(properties);
    }

    for (Class superClass = class_getSuperclass(objcClass); superClass; superClass = class_getSuperclass(superClass)) {
        properties = class_copyPropertyList(superClass, &outCount);
        for (uint i = 0; i < outCount; ++i) {
            propertyName = [NSString stringWithCString:property_getName(properties[i]) encoding:NSUTF8StringEncoding];
            if ([fetchedProperties containsObject:propertyName]) {
                continue;
            }
            else {
                [fetchedProperties addObject:propertyName];
            }
            [outDictionary[@"properties"] addObject:@{
                @"name": propertyName,
                @"attributes": [NSString stringWithCString:property_getAttributes(properties[i]) encoding:NSUTF8StringEncoding],
            }];
        }
        if (properties) {
            free(properties);
        }
    }
}

void addMethodsToDictionary(Class objcClass, NSDictionary *outDictionary)
{
    uint outCount = 0;
    Method *methods = class_copyMethodList(object_getClass(objcClass), &outCount);
    uint argsCount = 0;
    NSMutableArray *argsTypes;
    char *methodArgumentsTypes;
    char *methodReturnType;
    for (uint i = 0; i < outCount; ++i) {
        argsCount = method_getNumberOfArguments(methods[i]);
        argsTypes = [NSMutableArray new];
        for (uint j = 0; j < argsCount; ++j) {
            methodArgumentsTypes = method_copyArgumentType(methods[i], j);
            [argsTypes addObject: [NSString stringWithCString:methodArgumentsTypes encoding:NSUTF8StringEncoding]];
            if (methodArgumentsTypes) {
                free(methodArgumentsTypes);
            }
        }
        methodReturnType = method_copyReturnType(methods[i]);
        [outDictionary[@"methods"] addObject:@{
            @"name": [NSString stringWithCString:sel_getName(method_getName(methods[i])) encoding:NSUTF8StringEncoding],
            @"address": [NSNumber numberWithLong:(uintptr_t)method_getImplementation(methods[i])],
            @"is_class": @YES,
            @"type": [NSString stringWithCString:method_getTypeEncoding(methods[i]) encoding:NSUTF8StringEncoding],
            @"return_type": [NSString stringWithCString:methodReturnType encoding:NSUTF8StringEncoding],
            @"args_types": argsTypes,
        }];
        if (methodReturnType) {
            free(methodReturnType);
        }
    }
    if (methods) {
        free(methods);
    }

    methods = class_copyMethodList(objcClass, &outCount);
    for (uint i = 0; i < outCount; ++i) {
        argsCount = method_getNumberOfArguments(methods[i]);
        argsTypes = [NSMutableArray new];
        for (uint j = 0; j < argsCount; ++j) {
            methodArgumentsTypes = method_copyArgumentType(methods[i], j);
            [argsTypes addObject: [NSString stringWithCString:methodArgumentsTypes encoding:NSUTF8StringEncoding]];
            if (methodArgumentsTypes) {
                free(methodArgumentsTypes);
            }
        }
        methodReturnType = method_copyReturnType(methods[i]);
        [outDictionary[@"methods"] addObject:@{
            @"name": [NSString stringWithCString:sel_getName(method_getName(methods[i])) encoding:NSUTF8StringEncoding],
            @"address": [NSNumber numberWithLong:(uintptr_t)method_getImplementation(methods[i])],
            @"is_class": @NO,
            @"type": [NSString stringWithCString:method_getTypeEncoding(methods[i]) encoding:NSUTF8StringEncoding],
            @"return_type": [NSString stringWithCString:methodReturnType encoding:NSUTF8StringEncoding],
            @"args_types": argsTypes,
        }];
        if (methodReturnType) {
            free(methodReturnType);
        }
    }
    if (methods) {
        free(methods);
    }
}

NSString* getDictionaryJsonString(NSDictionary *classDescription)
{
    NSData *data = [NSJSONSerialization dataWithJSONObject:classDescription options:0 error:nil];
    return [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
}
