#ifdef __APPLE__
#include <mach/mach_init.h>
#include <mach/message.h>
#include <mach/vm_map.h>
#endif// __APPLE__

#include "routines.h"

#include "protos/rpc_api.pb-c.h"

#include <dirent.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

#define MAX_ERROR_MSG_LEN 256

static routine_status_t routine_dlopen(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg);
static routine_status_t routine_dlclose(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg);
static routine_status_t routine_dlsym(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg);
static routine_status_t routine_peek(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg);
static routine_status_t routine_poke(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg);
static routine_status_t routine_call(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg);
static routine_status_t routine_listdir(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg);
static routine_status_t routine_close_client(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg);
static routine_status_t routine_exec(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg);

static void cleanup_peek(ProtobufCMessage *reply);
static void cleanup_listdir(ProtobufCMessage *reply);

// Darwin specific
#if __APPLE__
routine_status_t routine_show_class(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg);
routine_status_t routine_show_object(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg);
routine_status_t routine_get_class_list(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg);
routine_status_t routine_get_dummy_block(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg);

void cleanup_show_class(ProtobufCMessage *reply);
void cleanup_show_object(ProtobufCMessage *reply);
void cleanup_get_class_list(ProtobufCMessage *reply);
#endif// __APPLE__

void call_function(intptr_t address, size_t va_list_index, size_t argc, Rpc__Api__Argument **p_argv,
                   Rpc__Api__ReplyCall *resp);

/**
 * @brief An array representing the mapping of RPC message IDs to their corresponding RPC routines.
 *
 * This array maps specific RPC message IDs to their handler routines, along with metadata associated
 * with each routine such as request and reply descriptors, a human-readable name, and an optional
 * cleanup function. It supports a range of core RPC operations as well as platform-specific routines
 * (e.g., Apple-specific routines).
 *
 * The `rpc_routines` array is indexed using enumerated message IDs (e.g., `RPC__MSG_ID__REQ_DLOPEN`)
 * and allows the RPC mechanism to dynamically resolve and invoke the appropriate handler for incoming
 * requests.
 *
 * Each entry in this array contains:
 * - `routine`: Pointer to the function handling the specific RPC request.
 * - `request_descriptor`: Pointer to the descriptor defining the format of the request.
 * - `reply_descriptor`: Pointer to the descriptor defining the format of the reply.
 * - `name`: A string representing the name of the routine (used for logging/troubleshooting).
 * - `cleanup`: A pointer to an optional cleanup function, executed after the routine (can be NULL).
 *
 * The array size is defined by `RPC__PROTOCOL_CONSTANTS__RPC_MAX_REQ_MSG_ID`, ensuring sufficient
 * space to accommodate all defined message IDs.
 *
 */
const rpc_routine_entry_t rpc_routines[RPC__PROTOCOL_CONSTANTS__RPC_MAX_REQ_MSG_ID] = {
    [RPC__API__MSG_ID__REQ_DLOPEN] = {.routine = routine_dlopen,
                                      .request_descriptor = &rpc__api__request_dlopen__descriptor,
                                      .reply_descriptor = &rpc__api__reply_dlopen__descriptor,
                                      .name = "DLOPEN",
                                      .cleanup = NULL

    },
    [RPC__API__MSG_ID__REQ_DLCLOSE] = {.routine = routine_dlclose,
                                       .request_descriptor = &rpc__api__request_dlclose__descriptor,
                                       .reply_descriptor = &rpc__api__reply_dlclose__descriptor,
                                       .name = "DLCLOSE",
                                       .cleanup = NULL},
    [RPC__API__MSG_ID__REQ_DLSYM] = {.routine = routine_dlsym,
                                     .request_descriptor = &rpc__api__request_dlsym__descriptor,
                                     .reply_descriptor = &rpc__api__reply_dlsym__descriptor,
                                     .name = "DLSYM",
                                     .cleanup = NULL},
    [RPC__API__MSG_ID__REQ_PEEK] = {.routine = routine_peek,
                                    .request_descriptor = &rpc__api__request_peek__descriptor,
                                    .reply_descriptor = &rpc__api__reply_peek__descriptor,
                                    .name = "PEEK",
                                    .cleanup = cleanup_peek},
    [RPC__API__MSG_ID__REQ_POKE] = {.routine = routine_poke,
                                    .request_descriptor = &rpc__api__request_poke__descriptor,
                                    .reply_descriptor = &rpc__api__reply_poke__descriptor,
                                    .name = "POKE",
                                    .cleanup = NULL},
    [RPC__API__MSG_ID__REQ_CALL] = {.routine = routine_call,
                                    .request_descriptor = &rpc__api__request_call__descriptor,
                                    .reply_descriptor = &rpc__api__reply_call__descriptor,
                                    .name = "CALL",
                                    .cleanup = NULL},
    [RPC__API__MSG_ID__REQ_LIST_DIR] = {.routine = routine_listdir,
                                        .request_descriptor = &rpc__api__request_list_dir__descriptor,
                                        .reply_descriptor = &rpc__api__reply_list_dir__descriptor,
                                        .name = "LISTDIR",
                                        .cleanup = cleanup_listdir},
    [RPC__API__MSG_ID__REQ_CLOSE_CLIENT] =
    {
        .routine = routine_close_client,
        .request_descriptor = &rpc__api__request_close_client__descriptor,
        .reply_descriptor = &rpc__api__reply_close_client__descriptor,
        .name = "CLOSE_CLIENT",
        .cleanup = NULL,
    },
    [RPC__API__MSG_ID__REQ_EXEC] =
    {
        .routine = routine_exec,
        .request_descriptor = &rpc__api__request_exec__descriptor,
        .reply_descriptor = &rpc__api__reply_exec__descriptor,
        .name = "EXEC",
        .cleanup = NULL,
    },

    /* Apple-specific routines */
#if __APPLE__
    [RPC__API__MSG_ID__REQ_DUMMY_BLOCK] = {.routine = routine_get_dummy_block,
                                           .request_descriptor = &rpc__api__request_dummy_block__descriptor,
                                           .reply_descriptor = &rpc__api__reply_dummy_block__descriptor,
                                           .name = "DUMMY_BLOCK",
                                           .cleanup = NULL},
    [RPC__API__MSG_ID__REQ_SHOW_CLASS] = {.routine = routine_show_class,
                                          .request_descriptor = &rpc__api__request_show_class__descriptor,
                                          .reply_descriptor = &rpc__api__reply_show_class__descriptor,
                                          .name = "SHOW_CLASS",
                                          .cleanup = cleanup_show_class},
    [RPC__API__MSG_ID__REQ_SHOW_OBJECT] = {.routine = routine_show_object,
                                           .request_descriptor = &rpc__api__request_show_object__descriptor,
                                           .reply_descriptor = &rpc__api__reply_show_object__descriptor,
                                           .name = "SHOW_OBJECT",
                                           .cleanup = cleanup_show_object},
    [RPC__API__MSG_ID__REQ_GET_CLASS_LIST] = {.routine = routine_get_class_list,
                                              .request_descriptor = &rpc__api__request_get_class_list__descriptor,
                                              .reply_descriptor = &rpc__api__reply_get_class_list__descriptor,
                                              .name = "GET_CLASS_LIST",
                                              .cleanup = cleanup_get_class_list},
#endif// __APPLE__

};

typedef enum { MSG_ID_VALID = 0, MSG_ID_OUT_OF_BOUNDS, MSG_ID_NO_ROUTINE } msg_id_error_t;

/**
 * @brief Looks up the routine entry corresponding to the given message ID.
 *
 * This function retrieves the routine entry for the specified message ID. It validates
 * the message ID to ensure it is within the acceptable range and checks that the routine
 * entry is properly populated with required components.
 *
 * @param msg_id The message ID for which the routine entry is to be looked up. Must be
 *               greater than 0 and less than RPC__PROTOCOL_CONSTANTS__RPC_MAX_REQ_MSG_ID.
 * @param out_entry Pointer to a location where the found routine entry will be stored.
 *                  If the routine entry is valid, this pointer will point to the routine entry.
 *
 * @return A value of type `msg_id_error_t` indicating the result of the lookup.
 *         - MSG_ID_VALID: The routine entry was found and is valid.
 *         - MSG_ID_OUT_OF_BOUNDS: The provided message ID is outside the valid range.
 *         - MSG_ID_NO_ROUTINE: The routine entry is incomplete or not initialized correctly.
 */
static msg_id_error_t routine_lookup(uint32_t msg_id, const rpc_routine_entry_t **out_entry) {
    if (msg_id <= 0 || msg_id >= RPC__PROTOCOL_CONSTANTS__RPC_MAX_REQ_MSG_ID) { return MSG_ID_OUT_OF_BOUNDS; }

    const rpc_routine_entry_t *entry = &rpc_routines[msg_id];
    if (!entry->routine || !entry->request_descriptor || !entry->reply_descriptor) { return MSG_ID_NO_ROUTINE; }

    *out_entry = entry;
    return MSG_ID_VALID;
}

/**
 * Sends an error reply by populating the provided Rpc__RpcMessage object
 * with an error message and corresponding error details. This function
 * formats the provided error message using `printf`-like format specifiers.
 * The error will be packed into the message's payload for transmission.
 *
 * @param out Pointer to the output Rpc__RpcMessage object where the error
 *            reply will be stored.
 * @param fmt Format string for the error message. This string is followed
 *            by any additional arguments required by the format string.
 */
static void reply_error(Rpc__RpcMessage *out, const char *fmt, ...) {
    Rpc__Api__ReplyError err = RPC__API__REPLY_ERROR__INIT;
    static char error_buffer[MAX_ERROR_MSG_LEN];

    va_list args;
    va_start(args, fmt);
    vsnprintf(error_buffer, sizeof(error_buffer), fmt, args);
    va_end(args);

    err.message = error_buffer;
    err.errno_code = errno;

    out->msg_id = RPC__PROTOCOL_CONSTANTS__REP_ERROR;

    const size_t size = rpc__api__reply_error__get_packed_size(&err);
    uint8_t *data = malloc(size);
    if (!data) {
        out->payload.data = NULL;
        out->payload.len = 0;
        return;
    }

    rpc__api__reply_error__pack(&err, data);
    out->payload.data = data;
    out->payload.len = size;
}

/**
 * Dispatches an RPC request message to the appropriate routine based on its message ID, processes it,
 * and prepares a corresponding reply message.
 *
 * The function performs the following steps:
 * 1. Initializes the reply message.
 * 2. Looks up the routine corresponding to the message ID in the request message.
 * 3. Unpacks the request payload and invokes the identified routine.
 * 4. Handles the routine's reply or any errors that occur during processing.
 *
 * @param request_msg The incoming RPC request message containing the message ID and payload.
 * @param reply_msg The outgoing RPC reply message to contain the processed reply or an error message.
 */
void rpc_dispatch(const Rpc__RpcMessage *request_msg, Rpc__RpcMessage *reply_msg) {
    ProtobufCMessage *request = NULL;
    ProtobufCMessage *reply = NULL;
    const struct rpc_routine_entry *entry = NULL;

    rpc__rpc_message__init(reply_msg);
    reply_msg->magic = RPC__PROTOCOL_CONSTANTS__MESSAGE_MAGIC;

    switch (routine_lookup(request_msg->msg_id, &entry)) {
    case MSG_ID_OUT_OF_BOUNDS: reply_error(reply_msg, "Out of bound msg_id %d: must be 1-%d", request_msg->msg_id,
                                           RPC__PROTOCOL_CONSTANTS__RPC_MAX_REQ_MSG_ID - 1);
        goto error;
    case MSG_ID_NO_ROUTINE: reply_error(reply_msg, "No routine configured for msg_id %d", request_msg->msg_id);
        goto error;
    case MSG_ID_VALID: break;
    }

    TRACE("Dispatching msg_id: %d (%s)", request_msg->msg_id, entry->name);

    request =
        protobuf_c_message_unpack(entry->request_descriptor, NULL, request_msg->payload.len, request_msg->payload.data);
    CHECK(request);

    // Invoke routine
    const routine_status_t result = entry->routine(request, &reply);

    switch (result) {
    case ROUTINE_SERVER_ERROR: {
        reply_error(reply_msg, "Server error on msg_id %d (%s)", request_msg->msg_id, entry->name);
        break;
    }
    case ROUTINE_PROTOCOL_ERROR: {
        reply_error(reply_msg, "Protocol error on msg_id %d (%s)", request_msg->msg_id, entry->name);
        break;
    }
    case ROUTINE_SUCCESS: {
        reply_msg->msg_id = request_msg->msg_id + RPC__PROTOCOL_CONSTANTS__RPC_MAX_REQ_MSG_ID;
        const size_t packed_size = protobuf_c_message_get_packed_size(reply);
        uint8_t *packed_data = (uint8_t *) malloc(packed_size);
        CHECK(packed_data);
        protobuf_c_message_pack(reply, packed_data);
        reply_msg->payload.data = packed_data;
        reply_msg->payload.len = packed_size;
        if (entry->cleanup) { entry->cleanup(reply); }
        break;
    }
    }

error:
    if (request) {
        protobuf_c_message_free_unpacked(request, NULL);
        request = NULL;
    }
}

/**
 * Handles the dlopen routine by processing the input ProtobufCMessage and creating
 * the corresponding output ProtobufCMessage. This function wraps the dlopen system
 * call, initializing and returning a handle to a dynamic library specified in the
 * input message. It prepares the output message including the library handle.
 * Errors in allocation or other failures result in an error status.
 *
 * @param  in_msg  The input ProtobufCMessage containing the dlopen request.
 *                      It is expected to conform to the Rpc__Api__RequestDlopen structure.
 * @param out_msg A pointer to the output ProtobufCMessage where the reply
 *                      message will be stored. The function allocates memory for this,
 *                      which must be handled appropriately by the caller.
 *
 * @return ROUTINE_SUCCESS on successful execution of the routine.
 *         ROUTINE_SERVER_ERROR in case of an error during execution.
 */
static routine_status_t routine_dlopen(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg) {
    const Rpc__Api__RequestDlopen *request_dlopen = (const Rpc__Api__RequestDlopen *) in_msg;
    Rpc__Api__ReplyDlopen *reply_dlopen = malloc(sizeof *reply_dlopen);
    CHECK(reply_dlopen != NULL);
    rpc__api__reply_dlopen__init(reply_dlopen);
    *out_msg = (ProtobufCMessage *) reply_dlopen;

    reply_dlopen->handle = (uint64_t) (uintptr_t) dlopen(request_dlopen->filename, request_dlopen->mode);

    return ROUTINE_SUCCESS;
error:
    return ROUTINE_SERVER_ERROR;
}

/**
 * Handles the dlclose routine by closing a shared library handle provided in the input message.
 *
 * This function extracts the handle from the input protobuf message, attempts to close the
 * specified shared library handle using the dlclose system call, and sets the result in the
 * output protobuf message. If memory allocation for the output message fails, the function
 * returns a server error status. The function assumes that the input message is correctly
 * formatted and contains a valid handle.
 *
 * @param in_msg A pointer to the input protobuf message containing the handle to be closed.
 *               This message is expected to be of type Rpc__Api__RequestDlclose.
 * @param out_msg A pointer to a pointer for the output protobuf message. The function allocates
 *                memory for this message, initializes it, and writes the result of the dlclose
 *                operation into it. This message is of type Rpc__Api__ReplyDlclose.
 * @return ROUTINE_SUCCESS if the operation completes successfully.
 *         ROUTINE_SERVER_ERROR if memory allocation for the output message fails.
 */
routine_status_t routine_dlclose(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg) {
    const Rpc__Api__RequestDlclose *request_dlclose = (const Rpc__Api__RequestDlclose *) in_msg;
    Rpc__Api__ReplyDlclose *reply_dlclose = malloc(sizeof *reply_dlclose);
    CHECK(reply_dlclose != NULL);
    rpc__api__reply_dlclose__init(reply_dlclose);
    *out_msg = (ProtobufCMessage *) reply_dlclose;

    reply_dlclose->res = (uint64_t) dlclose((void *) request_dlclose->handle);

    return ROUTINE_SUCCESS;
error:
    return ROUTINE_SERVER_ERROR;
}

/**
 * @brief Handles the dlsym routine to dynamically resolve symbols.
 *
 * This function processes an incoming ProtobufCMessage, interprets it as a
 * request to dynamically resolve a symbol using the `dlsym` function, and
 * generates a reply message with the result.
 *
 * @param in_msg Pointer to the input ProtobufCMessage representing the
 *            Rpc__Api__RequestDlsym request. This message contains the required
 *            data such as the handle and the symbol name to be resolved.
 * @param out_msg Pointer to a ProtobufCMessage pointer where the reply
 *             message (Rpc__Api__ReplyDlsym) will be stored after successful
 *             allocation and initialization. The reply message includes the
 *             resolved pointer.
 *
 * @return A value of type routine_status_t indicating the status of the
 *         operation. Returns ROUTINE_SUCCESS on success or a relevant
 *         error code on failure (e.g., ROUTINE_SERVER_ERROR for memory
 *         allocation failure).
 */
routine_status_t routine_dlsym(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg) {
    const Rpc__Api__RequestDlsym *request_dlsym = (const Rpc__Api__RequestDlsym *) in_msg;
    Rpc__Api__ReplyDlsym *reply_dlsym = malloc(sizeof *reply_dlsym);
    CHECK(reply_dlsym != NULL);
    rpc__api__reply_dlsym__init(reply_dlsym);
    *out_msg = (ProtobufCMessage *) reply_dlsym;

    reply_dlsym->ptr = (uint64_t) dlsym((void *) request_dlsym->handle, request_dlsym->symbol_name);

    TRACE("%s = %p", request_dlsym->symbol_name, reply_dlsym->ptr);
    return ROUTINE_SUCCESS;
error:
    return ROUTINE_SERVER_ERROR;
}

/**
 * Handles a peek operation for a routine by processing an input ProtobufCMessage
 * and producing an output ProtobufCMessage containing the requested data.
 *
 * @param in_msg The input ProtobufCMessage containing the request data.
 *               This must be of type Rpc__Api__RequestPeek.
 * @param out_msg A pointer to store the ProtobufCMessage containing the reply
 *                data. This will be allocated within the method. The caller is
 *                responsible for freeing the memory.
 * @return A routine_status_t indicating the status of the operation:
 *         ROUTINE_SUCCESS on success, ROUTINE_PROTOCOL_ERROR if the operation
 *         encounters a protocol error, or ROUTINE_SERVER_ERROR if a server
 *         error occurs.
 */
static routine_status_t routine_peek(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg) {
    const Rpc__Api__RequestPeek *request_peek = (const Rpc__Api__RequestPeek *) in_msg;
    Rpc__Api__ReplyPeek *reply_peek = malloc(sizeof *reply_peek);
    CHECK(reply_peek != NULL);
    rpc__api__reply_peek__init(reply_peek);
    *out_msg = (ProtobufCMessage *) reply_peek;

    uint8_t *buffer = NULL;

#if defined(__APPLE__) && defined(SAFE_READ_WRITES)
    mach_msg_type_number_t size;

    if (vm_read(mach_task_self(), (vm_address_t) request_peek->address, (mach_vm_size_t) request_peek->size,
                (vm_offset_t *) &buffer, &size)
        != KERN_SUCCESS) { return ROUTINE_PROTOCOL_ERROR; }
    reply_peek->data.data = buffer;
    reply_peek->data.len = (size_t) size;

#else
    // Best-effort: copy from the requested address. If the address is invalid, this may fault.
    buffer = (uint8_t *) malloc(request_peek->size);
    CHECK(buffer != NULL);
    memcpy(buffer, (const void *) (uintptr_t) request_peek->address, request_peek->size);

    reply_peek->data.data = buffer;
    reply_peek->data.len = request_peek->size;

#endif

    return ROUTINE_SUCCESS;

error:
    safe_free(reply_peek);
    return ROUTINE_SERVER_ERROR;
}

/**
 * Attempts to write data to a specified memory address based on information
 * contained within a ProtobufCMessage request. A reply message is allocated
 * with the result of the operation.
 *
 * @param in_msg The input ProtobufCMessage containing the request data.
 *               This is expected to be of type Rpc__Api__RequestPoke.
 * @param out_msg A pointer to a ProtobufCMessage pointer that will be set
 *                to the allocated reply message of type Rpc__Api__ReplyPoke.
 *
 * @return ROUTINE_SUCCESS if the operation completes successfully.
 *         ROUTINE_PROTOCOL_ERROR if an error occurs during memory write.
 *         ROUTINE_SERVER_ERROR if a server-side error occurs, such as memory
 *         allocation failure.
 */
static routine_status_t routine_poke(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg) {
    const Rpc__Api__RequestPoke *request_poke = (const Rpc__Api__RequestPoke *) in_msg;
    Rpc__Api__ReplyPoke *reply_poke = malloc(sizeof *reply_poke);
    CHECK(reply_poke != NULL);
    rpc__api__reply_poke__init(reply_poke);
    *out_msg = (ProtobufCMessage *) reply_poke;

#if defined(__APPLE__) && defined(SAFE_READ_WRITES)
    if (vm_write(mach_task_self(), (vm_address_t) request_poke->address, (vm_offset_t) request_poke->data.data,
                 (mach_msg_type_number_t) request_poke->data.len)
        != KERN_SUCCESS) { return ROUTINE_PROTOCOL_ERROR; }
#else
    // Best-effort write; may fault if the address is invalid.
    memcpy((void *) (uintptr_t) request_poke->address, request_poke->data.data, request_poke->data.len);
#endif

    return ROUTINE_SUCCESS;

error:
    safe_free(reply_poke);
    return ROUTINE_SERVER_ERROR;
}

/**
 * Handles a routine call by processing the input `ProtobufCMessage` and producing an output `ProtobufCMessage`.
 *
 * This function initializes and populates a reply message based on the provided input message. If necessary,
 * it manages platform-specific considerations such as ARM architecture-specific handling.
 *
 * @param in_msg Pointer to the input `ProtobufCMessage`, expected to be of type `Rpc__Api__RequestCall`.
 * @param out_msg Pointer to a location where the pointer to the initialized and populated output
 *                     `ProtobufCMessage` will be stored. On success, this will point to a newly allocated
 *                     `Rpc__Api__ReplyCall` structure.
 *
 * @return Returns a `routine_status_t` indicating the status of the operation:
 *         - `ROUTINE_SUCCESS` if the operation completed successfully.
 *         - `ROUTINE_SERVER_ERROR` in case of an error, such as memory allocation failure.
 */
static routine_status_t routine_call(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg) {
    const Rpc__Api__RequestCall *request_call = (const Rpc__Api__RequestCall *) in_msg;
    Rpc__Api__ReplyCall *reply_poke = malloc(sizeof *reply_poke);
    CHECK(reply_poke != NULL);
    rpc__api__reply_call__init(reply_poke);
    *out_msg = (ProtobufCMessage *) reply_poke;

#ifdef __ARM_ARCH_ISA_A64
    // Allocate nested return-registers on heap so it survives until packing.
    Rpc__Api__ReturnRegistersArm *regs = malloc(sizeof *regs);
    CHECK(regs != NULL);
    rpc__api__return_registers_arm__init(regs);
    reply_poke->arm_registers = regs;
    reply_poke->return_values_case = RPC__API__REPLY_CALL__RETURN_VALUES_ARM_REGISTERS;
#else
    reply_poke->return_values_case = RPC__API__REPLY_CALL__RETURN_VALUES_RETURN_VALUE;
#endif

    TRACE("address: %p", (void *) (uintptr_t) request_call->address);
    call_function(request_call->address, request_call->va_list_index, request_call->n_argv, request_call->argv,
                  reply_poke);

    return ROUTINE_SUCCESS;

error:
#ifdef __ARM_ARCH_ISA_A64
    if (reply_poke && reply_poke->arm_registers) {
        free(reply_poke->arm_registers);
        reply_poke->arm_registers = NULL;
    }
#endif
    safe_free(reply_poke);
    return ROUTINE_SERVER_ERROR;
}

/**
 * Closes a client session and prepares a reply message.
 *
 * @param in_msg The input message. It is not used in this function and can be NULL.
 * @param out_msg A pointer to a pointer that will be set to a newly allocated output message.
 *                The caller must free this output message after use.
 * @return Returns ROUTINE_SUCCESS if the operation is successful, and ROUTINE_SERVER_ERROR
 *         if a memory allocation or other error occurs.
 */
static routine_status_t routine_close_client(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg) {
    (void) in_msg;
    Rpc__Api__ReplyCloseClient *reply_close = malloc(sizeof *reply_close);
    CHECK(reply_close != NULL);
    rpc__api__reply_close_client__init(reply_close);
    *out_msg = (ProtobufCMessage *) reply_close;

    return ROUTINE_SUCCESS;
error:
    return ROUTINE_SERVER_ERROR;
}

/**
 * This function processes a directory listing request encoded within a Protobuf message,
 * retrieves the directory entries from the specified path, and encodes the results
 * into the output Protobuf message, including file type, name, and additional metadata
 * such as stat and lstat information.
 *
 * @param in_msg Input Protobuf message containing the path for the directory to list.
 *               Must be of type `Rpc__Api__RequestListDir` and include a valid `path`.
 * @param out_msg Output Protobuf message containing the results of the directory listing.
 *                Will be populated as a `Rpc__Api__ReplyListDir` message with directory entries.
 *
 * @return A `routine_status_t` status code:
 *         - `ROUTINE_SUCCESS` if successful.
 *         - `ROUTINE_PROTOCOL_ERROR` if an invalid input or a protocol issue occurs.
 *         - `ROUTINE_SERVER_ERROR` if an error occurs during processing, such as memory
 *           allocation failure or filesystem errors.
 */
static routine_status_t routine_listdir(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg) {
    const Rpc__Api__RequestListDir *request_list_dir = (const Rpc__Api__RequestListDir *) in_msg;
    Rpc__Api__ReplyListDir *reply_list_dir = malloc(sizeof *reply_list_dir);
    DIR *dirp = NULL;
    CHECK(reply_list_dir != NULL);
    rpc__api__reply_list_dir__init(reply_list_dir);
    *out_msg = (ProtobufCMessage *) reply_list_dir;

    struct dirent *entry = NULL;
    size_t entry_count = 0, idx = 0;

    TRACE("LISTDIR: path='%s'", request_list_dir->path ? request_list_dir->path : "(null)");
    CHECK(request_list_dir->path && request_list_dir->path[0] != '\0');

    // First pass: count entries
    dirp = opendir(request_list_dir->path);
    if (dirp == NULL) { return ROUTINE_PROTOCOL_ERROR; }
    while ((entry = readdir(dirp)) != NULL) { entry_count++; }
    CHECK(closedir(dirp) == 0);
    dirp = NULL;

    reply_list_dir->dir_entries = NULL;
    reply_list_dir->n_dir_entries = 0;

    if (entry_count == 0) { return ROUTINE_SUCCESS; }

    reply_list_dir->dir_entries = (Rpc__Api__DirEntry **) calloc(entry_count, sizeof(Rpc__Api__DirEntry *));
    CHECK(reply_list_dir->dir_entries != NULL);

    // Second pass: populate entries
    dirp = opendir(request_list_dir->path);
    CHECK(dirp != NULL);

    while ((entry = readdir(dirp)) != NULL && idx < entry_count) {
        Rpc__Api__DirEntry *d_entry = NULL;
        Rpc__Api__DirEntryStat *s_stat = NULL;
        Rpc__Api__DirEntryStat *l_stat = NULL;

        struct stat system_stat;
        struct stat system_lstat;
        memset(&system_stat, 0, sizeof(system_stat));
        memset(&system_lstat, 0, sizeof(system_lstat));

        char fullpath[FILENAME_MAX];
        int n = snprintf(fullpath, sizeof(fullpath), "%s/%s", request_list_dir->path, entry->d_name);
        CHECK(n > 0 && (size_t) n < sizeof(fullpath));

        u64 stat_err = 0, lstat_err = 0;
        if (lstat(fullpath, &system_lstat) != 0) { lstat_err = (u64) errno; }
        if (stat(fullpath, &system_stat) != 0) { stat_err = (u64) errno; }

        d_entry = (Rpc__Api__DirEntry *) malloc(sizeof *d_entry);
        s_stat = (Rpc__Api__DirEntryStat *) malloc(sizeof *s_stat);
        l_stat = (Rpc__Api__DirEntryStat *) malloc(sizeof *l_stat);
        CHECK(d_entry && s_stat && l_stat);

        rpc__api__dir_entry__init(d_entry);
        rpc__api__dir_entry_stat__init(s_stat);
        rpc__api__dir_entry_stat__init(l_stat);

        // Fill 'stat'
        s_stat->errno1 = stat_err;
        s_stat->st_dev = system_stat.st_dev;
        s_stat->st_mode = system_stat.st_mode;
        s_stat->st_nlink = system_stat.st_nlink;
        s_stat->st_ino = system_stat.st_ino;
        s_stat->st_uid = system_stat.st_uid;
        s_stat->st_gid = system_stat.st_gid;
        s_stat->st_rdev = system_stat.st_rdev;
        s_stat->st_size = system_stat.st_size;
        s_stat->st_blocks = system_stat.st_blocks;
        s_stat->st_blksize = system_stat.st_blksize;
        s_stat->st_atime1 = system_stat.st_atime;
        s_stat->st_mtime1 = system_stat.st_mtime;
        s_stat->st_ctime1 = system_stat.st_ctime;

        // Fill 'lstat'
        l_stat->errno1 = lstat_err;
        l_stat->st_dev = system_lstat.st_dev;
        l_stat->st_mode = system_lstat.st_mode;
        l_stat->st_nlink = system_lstat.st_nlink;
        l_stat->st_ino = system_lstat.st_ino;
        l_stat->st_uid = system_lstat.st_uid;
        l_stat->st_gid = system_lstat.st_gid;
        l_stat->st_rdev = system_lstat.st_rdev;
        l_stat->st_size = system_lstat.st_size;
        l_stat->st_blocks = system_lstat.st_blocks;
        l_stat->st_blksize = system_lstat.st_blksize;
        l_stat->st_atime1 = system_lstat.st_atime;
        l_stat->st_mtime1 = system_lstat.st_mtime;
        l_stat->st_ctime1 = system_lstat.st_ctime;

        d_entry->d_type = entry->d_type;
        d_entry->d_name = strdup(entry->d_name);
        CHECK(d_entry->d_name != NULL);
        d_entry->stat = s_stat;
        d_entry->lstat = l_stat;

        reply_list_dir->dir_entries[idx++] = d_entry;
        reply_list_dir->n_dir_entries = idx;// progressive for cleanup safety
    }

    CHECK(closedir(dirp) == 0);
    dirp = NULL;

    return ROUTINE_SUCCESS;

error:
    safe_free(dirp);
    if (reply_list_dir) {
        if (reply_list_dir->dir_entries) {
            for (size_t i = 0; i < reply_list_dir->n_dir_entries; ++i) {
                if (!reply_list_dir->dir_entries[i]) { continue; }
                safe_free(reply_list_dir->dir_entries[i]->d_name);
                safe_free(reply_list_dir->dir_entries[i]->stat);
                safe_free(reply_list_dir->dir_entries[i]->lstat);
                safe_free(reply_list_dir->dir_entries[i]);
            }
            safe_free(reply_list_dir->dir_entries);
        }
        free(reply_list_dir);
    }
    return ROUTINE_SERVER_ERROR;
}

/**
 * Waits for a specific thread process to terminate and captures its exit status.
 *
 * @param pid The process ID of the thread to wait for. This must be a valid PID.
 */
static void thread_waitpid(pid_t pid) {
    TRACE("enter");
    s32 err;
    waitpid(pid, &err, 0);
}

typedef struct {
    int sockfd;
    pid_t pid;
} thread_notify_client_spawn_error_t;

/**
 * Executes a routine based on the provided input message, spawns a process if necessary,
 * and prepares an output message with the results.
 *
 * This function handles both background and foreground process execution. If running
 * in the background, a monitoring thread is created for the process. If running in the
 * foreground, process-related information is stored in a global structure.
 *
 * @param in_msg The input Protocol Buffer message containing the execution request details.
 *               This should be a message of type Rpc__Api__RequestExec.
 * @param out_msg A pointer to a pointer that will be set to the output Protocol Buffer
 *                message containing the execution result. This will be a message
 *                of type Rpc__Api__ReplyExec.
 * @return A status code indicating the result of the routine execution. Possible values
 *         include:
 *         - ROUTINE_SUCCESS: The routine completed successfully.
 *         - ROUTINE_PROTOCOL_ERROR: There was an error in the protocol or input processing.
 *         - ROUTINE_SERVER_ERROR: A server-side error occurred during execution.
 */
static routine_status_t routine_exec(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg) {
    const Rpc__Api__RequestExec *request_exec = (const Rpc__Api__RequestExec *) in_msg;
    Rpc__Api__ReplyExec *reply_exec = malloc(sizeof *reply_exec);
    pid_t pid = INVALID_PID;

    CHECK(reply_exec != NULL);

    rpc__api__reply_exec__init(reply_exec);
    *out_msg = (ProtobufCMessage *) reply_exec;

    pthread_t thread = 0;
    thread_notify_client_spawn_error_t *thread_params = NULL;

    int master = -1;

    // Prepare argv/envp arrays (null-terminated)
    char **argv = NULL;
    char **envp = NULL;

    CHECK(request_exec->n_argv > 0);

    CHECK(copy_arr_with_null(&argv, request_exec->argv, request_exec->n_argv));
    CHECK(copy_arr_with_null(&envp, request_exec->envp, request_exec->n_envp));

    // Spawn
    CHECK(internal_spawn(request_exec->background, argv, request_exec->n_envp ? envp : environ, &pid, &master));

    reply_exec->pid = pid;

    if (request_exec->background) {
        if (master >= 0) { close(master); }
        CHECK(0 == pthread_create(&thread, NULL, (void *(*) (void *) ) thread_waitpid, (void *) (intptr_t) pid));
    } else {
        g_pending_pty.pid = pid;
        g_pending_pty.master = master;
        g_pending_pty.valid = true;
    }
error:
    safe_free(argv);
    safe_free(envp);
    safe_free(thread_params);

    if (INVALID_PID == pid) {
        TRACE("invalid pid");
        return ROUTINE_PROTOCOL_ERROR;
    }

    return ROUTINE_SUCCESS;
}

/**
 * Frees resources associated with a ProtobufCMessage of type Rpc__Api__ReplyPeek.
 *
 * Depending on the platform and configuration, it either deallocates memory
 * using `vm_deallocate` (for macOS with SAFE_READ_WRITES defined) or `safe_free`.
 *
 * @param reply Pointer to the ProtobufCMessage to be cleaned up.
 *              Expected to be of type Rpc__Api__ReplyPeek.
 */
static void cleanup_peek(ProtobufCMessage *reply) {
    Rpc__Api__ReplyPeek *reply_peek = (Rpc__Api__ReplyPeek *) reply;

#if defined(__APPLE__) && defined(SAFE_READ_WRITES)
    vm_deallocate(mach_task_self(), (vm_address_t) reply_peek->data.data, reply_peek->data.len);
#else
    safe_free(reply_peek->data.data);
#endif
}

/**
 * Cleans up the dynamically allocated memory associated with a directory listing reply.
 * This function ensures that all allocated memory for directory entries,
 * their associated stat and lstat structures, and names are properly freed.
 *
 * @param reply A pointer to a ProtobufCMessage structure cast to Rpc__Api__ReplyListDir.
 *              The function deallocates memory associated with this structure's
 *              directory entries and their components. If the reply or its directory
 *              entries are null, the function exits without performing any action.
 */
static void cleanup_listdir(ProtobufCMessage *reply) {
    Rpc__Api__ReplyListDir *reply_list_dir = (Rpc__Api__ReplyListDir *) reply;
    if (!reply_list_dir || !reply_list_dir->dir_entries) { return; }
    for (size_t i = 0; i < reply_list_dir->n_dir_entries; ++i) {
        Rpc__Api__DirEntry *e = reply_list_dir->dir_entries[i];
        if (!e) { continue; }
        if (e->d_name) {
            free(e->d_name);
            e->d_name = NULL;
        }
        if (e->stat) {
            free(e->stat);
            e->stat = NULL;
        }
        if (e->lstat) {
            free(e->lstat);
            e->lstat = NULL;
        }
        free(e);
        reply_list_dir->dir_entries[i] = NULL;
    }
    free(reply_list_dir->dir_entries);
    reply_list_dir->dir_entries = NULL;
    reply_list_dir->n_dir_entries = 0;
}