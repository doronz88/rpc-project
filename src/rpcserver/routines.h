#ifndef RPCSERVER_HANDLERS_H
#define RPCSERVER_HANDLERS_H
#include "common.h"
typedef enum {
    ROUTINE_SUCCESS = 0,
    ROUTINE_PROTOCOL_ERROR,
    ROUTINE_SERVER_ERROR,
} routine_status_t;

typedef routine_status_t (*rpc_routine_t)(const ProtobufCMessage *in_msg, ProtobufCMessage **out_msg);
typedef void (*routine_cleanup)(ProtobufCMessage *reply);

/**
 * @struct rpc_routine_entry
 * @brief Represents a single RPC routine entry.
 *
 * This structure is used to define an RPC routine, including its function,
 * associated request and reply descriptors, routine name, and cleanup function.
 */
typedef struct rpc_routine_entry {
    /**
     * @brief Defines a function pointer type for an RPC routine.
     *
     * This variable represents an RPC routine that processes an input message
     * and generates an output message. The routine is implemented as a function
     * following a specific signature to handle messages encoded using Protocol Buffers.
     *
     * The function takes a pointer to the input ProtobufCMessage as its first parameter
     * and a double pointer to the output ProtobufCMessage as its second parameter.
     * The function returns a value of type routine_status_t to indicate the operation result.
     *
     * This variable is typically used in RPC mechanism implementations where the handling
     * of protocol message routing depends on predefined routine callbacks.
     *
     */
    rpc_routine_t routine;
    /**
     * Pointer to a ProtobufCMessageDescriptor structure that describes the schema
     * of the protobuf message associated with the request. This descriptor
     * contains metadata about the structure, fields, and types of the protocol
     * buffer message, enabling serialization and deserialization of the message.
     */
    const ProtobufCMessageDescriptor *request_descriptor;
    /**
     * A pointer to a ProtobufCMessageDescriptor structure that represents the
     * descriptor of the message type used in the response of an RPC routine.
     *
     * This variable is used to describe the structure, fields, and properties
     * of the reply message associated with a specific RPC routine implementation.
     *
     * It enables serialization and deserialization of the reply message
     * in compliance with the Protobuf-C message format.
     */
    const ProtobufCMessageDescriptor *reply_descriptor;
    /**
     * Represents the name of an RPC routine.
     * This variable is a pointer to a constant character string that holds the name associated with a specific RPC routine.
     */
    const char *name;
    routine_cleanup cleanup; /**
     * Function pointer type that defines a cleanup routine for a ProtobufCMessage.
     * Used to release or manage resources associated with the given message.
     */

} rpc_routine_entry_t;

/**
 * @brief Array of RPC routine entries.
 *
 * This variable defines a static mapping of request message IDs
 * to their corresponding RPC routine implementations. Each entry
 * in the array contains a set of attributes that define the
 * behavior, request/response structure, and associated cleanup
 * procedures for the respective RPC routine.
 *
 * Each element of the array is represented as a structure with
 * the following fields:
 * - `routine`: Pointer to the function implementing the RPC routine.
 * - `request_descriptor`: Pointer to the descriptor for the request
 *                         structure associated with the RPC routine.
 * - `reply_descriptor`: Pointer to the descriptor for the reply
 *                       structure associated with the RPC routine.
 * - `name`: Name of the RPC routine for identification or debugging.
 * - `cleanup`: Optional pointer to a cleanup function, which is executed
 *              after the RPC routine if set. If no cleanup is required,
 *              this is set to `NULL`.
 *
 * Routines are indexed by specific request message IDs defined
 * by the protocol constants (e.g., `RPC__MSG_ID__REQ_DLOPEN`).
 * Apple-specific routines are conditionally included based on
 * the target platform.
 *
 * The array size is defined as `RPC__PROTOCOL_CONSTANTS__RPC_MAX_REQ_MSG_ID`
 * to accommodate all possible routine entries as per the protocol.
 *
 * @note The Apple-specific routines are compiled and included only
 *       if the code is built on an Apple-based system (`__APPLE__`).
 */
extern const rpc_routine_entry_t rpc_routines[];

/**
 * Handles the dispatch of an RPC request message by identifying and executing
 * the appropriate routine based on the message ID. The reply message is
 * populated based on the routine's execution outcome.
 *
 * @param request_msg The RPC request message containing the message ID to
 *                    identify the desired routine and its payload.
 * @param reply_msg   The RPC reply message to be populated with the result
 *                    of the routine execution or an error response.
 */
void rpc_dispatch(const Rpc__RpcMessage *request_msg, Rpc__RpcMessage *reply_msg);
#endif//RPCSERVER_HANDLERS_H
