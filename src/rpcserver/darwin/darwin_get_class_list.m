#include "../common.h"
#include "darwin.h"
#include <Foundation/Foundation.h>
#include <objc/objc.h>
#include <objc/runtime.h>

bool handle_get_class_list(int sockfd, Rpc__CmdGetClassList *cmd) {
  TRACE("handle_get_class_list");
  Rpc__ResponseGetClassList resp_class_list = RPC__RESPONSE_GET_CLASS_LIST__INIT;
  Class *class_list = NULL;
  bool ret = false;

  u32 count = objc_getClassList(NULL, 0);
  CHECK(count > 0)
  TRACE("reporting class list: %d", count);
  resp_class_list.classes = malloc(sizeof(Rpc__ObjcClass *) * count);
  CHECK(resp_class_list.classes != NULL);

  class_list = malloc(sizeof(Class) * count);
  CHECK(class_list != NULL);

  count = objc_getClassList(class_list, count);
  for (int i = 0; i < count; ++i) {
    const char *name = class_getName(class_list[i]);

    resp_class_list.classes[i] = malloc(sizeof(Rpc__ObjcClass));
    rpc__objc_class__init(resp_class_list.classes[i]);
    resp_class_list.classes[i]->address = (uint64_t) class_list[i];
    resp_class_list.classes[i]->name = strdup(name);
  }
  resp_class_list.n_classes = count;
  CHECK(send_response(sockfd, (ProtobufCMessage *) &resp_class_list));
  ret = true;

error:
  if (resp_class_list.classes) {
    for (int i = 0; i < resp_class_list.n_classes; i++) {
          safe_free((void **) &resp_class_list.classes[i]->name);
          safe_free((void **) &resp_class_list.classes[i]);
      }
    safe_free((void **) &resp_class_list.classes);
  }
  safe_free((void **) &class_list);
  return ret;
}
