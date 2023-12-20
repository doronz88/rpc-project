#ifndef __DARWIN_H_
#define __DARWIN_H_
#include <stdint.h>

#include <Foundation/Foundation.h>
#include <objc/objc.h>
#include <objc/runtime.h>

void addProtocolsToDictionary(Class objcClass, NSDictionary *outDictionary);
void addIvarsToDictionary(Class objcClass, NSDictionary *outDictionary, id objcObject);
void addPropertiesToDictionary(Class objcClass, NSDictionary *outDictionary);
void addMethodsToDictionary(Class objcClass, NSDictionary *outDictionary);
NSString *getDictionaryJsonString(NSDictionary *classDescription);

#endif// __DARWIN_H_