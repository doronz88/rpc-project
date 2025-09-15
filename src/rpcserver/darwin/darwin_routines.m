#include "darwin.h"
#include <Foundation/Foundation.h>
#include <objc/objc.h>
#include <objc/runtime.h>
#include "../common.h"
#include "../routines.h"


void addProtocolsToDictionary(Class objcClass, NSDictionary *outDictionary);
void addIvarsToDictionary(Class objcClass, NSDictionary *outDictionary, id objcObject);
void addPropertiesToDictionary(Class objcClass, NSDictionary *outDictionary);
void addMethodsToDictionary(Class objcClass, NSDictionary *outDictionary);
NSString *getDictionaryJsonString(NSDictionary *classDescription);

NSString *getClassDescriptionStr(Class objcClass);
NSString *getObjectStr(id object);

void cleanup_show_class(ProtobufCMessage *reply);
void cleanup_show_object(ProtobufCMessage *reply);
void cleanup_get_class_list(ProtobufCMessage *reply);

void (^dummy_block)(void) = ^{
};

routine_status_t routine_get_class_list(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg) {
  (void) in_msg; // no fields needed from the request for now
  TRACE("Entered get_class_list (routine)");

  Rpc__Api__ReplyGetClassList *reply_get_class_list = NULL;
  Class *class_list = NULL;
  int count = 0;

  reply_get_class_list = (Rpc__Api__ReplyGetClassList *) malloc(sizeof *reply_get_class_list);
  CHECK(reply_get_class_list != NULL);
  rpc__api__reply_get_class_list__init(reply_get_class_list);
  reply_get_class_list->classes = NULL;
  reply_get_class_list->n_classes = 0;

  count = (int) objc_getClassList(NULL, 0);
  CHECK(count >= 0);

  if (count == 0) {
    // Return an empty list
    *out_msg = (ProtobufCMessage *) reply_get_class_list;
    return ROUTINE_SUCCESS;
  }

  reply_get_class_list->classes = (Rpc__Api__ObjcClass **) calloc((size_t) count, sizeof(Rpc__Api__ObjcClass *));
  CHECK(reply_get_class_list->classes != NULL);

  class_list = (Class *) malloc(sizeof(Class) * (size_t) count);
  CHECK(class_list != NULL);

  count = (int) objc_getClassList(class_list, count);
  CHECK(count >= 0);

  for (int i = 0; i < count; ++i) {
    const char *name = class_getName(class_list[i]);
    Rpc__Api__ObjcClass *cls = (Rpc__Api__ObjcClass *) malloc(sizeof *cls);
    CHECK(cls != NULL);
    rpc__api__objc_class__init(cls);
    cls->address = (uint64_t) (uintptr_t) class_list[i];
    cls->name = name ? strdup(name) : strdup("");
    CHECK(cls->name != NULL);
    reply_get_class_list->classes[i] = cls;
    reply_get_class_list->n_classes = (size_t) (i + 1);
  }

  *out_msg = (ProtobufCMessage *) reply_get_class_list;
  return ROUTINE_SUCCESS;

error:
  cleanup_get_class_list((ProtobufCMessage *)reply_get_class_list);
  safe_free(class_list);

  return ROUTINE_SERVER_ERROR;
}


routine_status_t routine_show_class(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg) {
  TRACE("Entered showclass (routine)");
  const Rpc__Api__RequestShowClass *request_show_class = (const Rpc__Api__RequestShowClass *) in_msg;
  Rpc__Api__ReplyShowClass *reply_show_class = NULL;

  reply_show_class = (Rpc__Api__ReplyShowClass *) malloc(sizeof *reply_show_class);
  CHECK(reply_show_class != NULL);
  rpc__api__reply_show_class__init(reply_show_class);

  NSString *response_str = getClassDescriptionStr((id) request_show_class->address);
  const char *utf8 = [response_str UTF8String];
  CHECK(utf8 != NULL);
  reply_show_class->description = strdup(utf8);
  CHECK(reply_show_class->description != NULL);

  *out_msg = (ProtobufCMessage *) reply_show_class;
  return ROUTINE_SUCCESS;

error:
  cleanup_show_class((ProtobufCMessage *)reply_show_class);
  safe_free(reply_show_class);

  return ROUTINE_SERVER_ERROR;
}

routine_status_t routine_show_object(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg) {
  TRACE("Calling objc_show_object (routine)");
  const Rpc__Api__RequestShowObject *request_show_object = (const Rpc__Api__RequestShowObject *) in_msg;
  Rpc__Api__ReplyShowObject *reply_show_object = NULL;

  reply_show_object = (Rpc__Api__ReplyShowObject *) malloc(sizeof *reply_show_object);
  CHECK(reply_show_object != NULL);
  rpc__api__reply_show_object__init(reply_show_object);

  NSString *response_str = getObjectStr((id) request_show_object->address);
  const char *utf8 = [response_str UTF8String];
  CHECK(utf8 != NULL);
  reply_show_object->description = strdup(utf8);
  CHECK(reply_show_object->description != NULL);

  *out_msg = (ProtobufCMessage *) reply_show_object;
  return ROUTINE_SUCCESS;

error:
    cleanup_show_object((ProtobufCMessage *)reply_show_object);
    safe_free(reply_show_object);

  return ROUTINE_SERVER_ERROR;
}

routine_status_t routine_get_dummy_block(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg) {
    Rpc__Api__ReplyDummyBlock *reply_dummy_block = malloc(sizeof *reply_dummy_block);
    CHECK(reply_dummy_block != NULL);
    rpc__api__reply_dummy_block__init(reply_dummy_block);
    reply_dummy_block->address = (uint64_t) dummy_block;
    reply_dummy_block->size = sizeof(dummy_block);

    *out_msg = (ProtobufCMessage *) reply_dummy_block;
    return ROUTINE_SUCCESS;
error:
    return ROUTINE_SERVER_ERROR;
}

void cleanup_get_class_list(ProtobufCMessage *reply) {
    Rpc__Api__ReplyGetClassList *r = (Rpc__Api__ReplyGetClassList *) reply;
    if (!r || !r->classes) return;
    for (size_t i = 0; i < r->n_classes; ++i) {
        Rpc__Api__ObjcClass *cls = r->classes[i];
        if (!cls) continue;
        safe_free(cls->name);
        safe_free(cls);
    }
    safe_free(r->classes);
}

void cleanup_show_class(ProtobufCMessage *reply) {
    Rpc__Api__ReplyShowClass *r = (Rpc__Api__ReplyShowClass *) reply;
    safe_free(r->description);
}

void cleanup_show_object(ProtobufCMessage *reply) {
    Rpc__Api__ReplyShowObject *r = (Rpc__Api__ReplyShowObject *) reply;
    safe_free(r->description);
}