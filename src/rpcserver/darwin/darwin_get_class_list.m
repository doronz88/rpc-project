#include "darwin.h"
#include "../common.h"
#include <objc/objc.h>
#include <objc/runtime.h>
#include <Foundation/Foundation.h>

int handle_get_class_list(int sockfd)
{
    TRACE("handle_get_class_list");

    Class* classes = NULL;
    u32 count = objc_getClassList(NULL, 0);

    TRACE("reporting class list: %d", count);
    CHECK(sendall(sockfd, (char *)&count, sizeof(count)));
    
    if (count > 0 ) {
        classes = malloc(sizeof(Class) * count);
        CHECK(classes != NULL);
        count = objc_getClassList(classes, count);

        for (int i=0; i<count; ++i) {
            const char *name = class_getName(classes[i]);
            u8 name_len = strlen(name);
            CHECK(sendall(sockfd, (char *)&name_len, sizeof(name_len)));
            CHECK(sendall(sockfd, name, name_len));
            CHECK(sendall(sockfd, (char *)classes[i], sizeof(classes[i])));
        }

        free(classes);
    }
    return 0;

error:
    if (classes) {
        free(classes);
    }

    TRACE("Failed to show class");
    return -1;
}
