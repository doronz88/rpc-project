#include "darwin.h"
#include "../common.h"
#include <objc/objc.h>
#include <objc/runtime.h>
#include <Foundation/Foundation.h>

int handle_get_class_list(int sockfd, Rpc__CmdGetClassList *cmd) {
    TRACE("handle_get_class_list");
    Rpc__Response response = RPC__RESPONSE__INIT;
    Rpc__ResponseGetClassList resp_class_list = RPC__RESPONSE_GET_CLASS_LIST__INIT;
    response.type_case = RPC__RESPONSE__TYPE_CLASS_LIST;
    Class *class_list = NULL;
    bool ret = RPC_FAILURE;

    u32 count = objc_getClassList(NULL, 0);
    if (count < 0) {
        return ret;
    }
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
    response.class_list = &resp_class_list;
    send_response(sockfd, &response);
    ret = RPC_SUCCESS;

    error:
    if (resp_class_list.classes) {
        for (int i = 0; i < resp_class_list.n_classes; i++) {
            SAFE_FREE(resp_class_list.classes[i]->name);
            SAFE_FREE(resp_class_list.classes[i]);
        }
        SAFE_FREE(resp_class_list.classes);
    }
    SAFE_FREE (class_list);
//    TRACE("Failed to show class");
    return ret;
}
