#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <stdint.h>

#include "eddsa.h"


#if defined(_WIN32) || defined(__CYGWIN__)
#define PYEDDSA_MODINIT_FUNC __declspec(dllexport) PyObject *
#elif defined(__GNUC__) || defined(__clang__)
#define PYEDDSA_MODINIT_FUNC __attribute__((visibility("default"))) PyObject *
#else
#define PYEDDSA_MODINIT_FUNC PyObject *
#endif


static int
expect_len(const Py_buffer *buffer, Py_ssize_t expected, const char *name)
{
    if (buffer->len == expected) {
        return 0;
    }
    PyErr_Format(PyExc_ValueError, "%s must be exactly %zd bytes", name, expected);
    return -1;
}

static PyObject *
py_ed25519_genpub(PyObject *self, PyObject *args)
{
    Py_buffer sec;
    PyObject *result;

    (void)self;
    if (!PyArg_ParseTuple(args, "y*:ed25519_genpub", &sec)) {
        return NULL;
    }
    if (expect_len(&sec, ED25519_KEY_LEN, "sec") < 0) {
        PyBuffer_Release(&sec);
        return NULL;
    }

    result = PyBytes_FromStringAndSize(NULL, ED25519_KEY_LEN);
    if (result != NULL) {
        ed25519_genpub((uint8_t *)PyBytes_AS_STRING(result), (const uint8_t *)sec.buf);
    }
    PyBuffer_Release(&sec);
    return result;
}

static PyObject *
py_ed25519_sign(PyObject *self, PyObject *args)
{
    Py_buffer sec;
    Py_buffer pub;
    Py_buffer data;
    PyObject *result;

    (void)self;
    if (!PyArg_ParseTuple(args, "y*y*y*:ed25519_sign", &sec, &pub, &data)) {
        return NULL;
    }
    if (expect_len(&sec, ED25519_KEY_LEN, "sec") < 0 ||
        expect_len(&pub, ED25519_KEY_LEN, "pub") < 0) {
        PyBuffer_Release(&data);
        PyBuffer_Release(&pub);
        PyBuffer_Release(&sec);
        return NULL;
    }

    result = PyBytes_FromStringAndSize(NULL, ED25519_SIG_LEN);
    if (result != NULL) {
        ed25519_sign((uint8_t *)PyBytes_AS_STRING(result),
            (const uint8_t *)sec.buf, (const uint8_t *)pub.buf,
            (const uint8_t *)data.buf, (size_t)data.len);
    }
    PyBuffer_Release(&data);
    PyBuffer_Release(&pub);
    PyBuffer_Release(&sec);
    return result;
}

static PyObject *
py_ed25519_verify(PyObject *self, PyObject *args)
{
    Py_buffer sig;
    Py_buffer pub;
    Py_buffer data;
    bool ok;

    (void)self;
    if (!PyArg_ParseTuple(args, "y*y*y*:ed25519_verify", &sig, &pub, &data)) {
        return NULL;
    }
    if (expect_len(&sig, ED25519_SIG_LEN, "sig") < 0 ||
        expect_len(&pub, ED25519_KEY_LEN, "pub") < 0) {
        PyBuffer_Release(&data);
        PyBuffer_Release(&pub);
        PyBuffer_Release(&sig);
        return NULL;
    }

    ok = ed25519_verify((const uint8_t *)sig.buf, (const uint8_t *)pub.buf,
        (const uint8_t *)data.buf, (size_t)data.len);
    PyBuffer_Release(&data);
    PyBuffer_Release(&pub);
    PyBuffer_Release(&sig);
    return PyBool_FromLong(ok);
}

static PyObject *
py_x25519_base(PyObject *self, PyObject *args)
{
    Py_buffer scalar;
    PyObject *result;

    (void)self;
    if (!PyArg_ParseTuple(args, "y*:x25519_base", &scalar)) {
        return NULL;
    }
    if (expect_len(&scalar, X25519_KEY_LEN, "scalar") < 0) {
        PyBuffer_Release(&scalar);
        return NULL;
    }

    result = PyBytes_FromStringAndSize(NULL, X25519_KEY_LEN);
    if (result != NULL) {
        x25519_base((uint8_t *)PyBytes_AS_STRING(result), (const uint8_t *)scalar.buf);
    }
    PyBuffer_Release(&scalar);
    return result;
}

static PyObject *
py_x25519(PyObject *self, PyObject *args)
{
    Py_buffer scalar;
    Py_buffer point;
    PyObject *result;

    (void)self;
    if (!PyArg_ParseTuple(args, "y*y*:x25519", &scalar, &point)) {
        return NULL;
    }
    if (expect_len(&scalar, X25519_KEY_LEN, "scalar") < 0 ||
        expect_len(&point, X25519_KEY_LEN, "point") < 0) {
        PyBuffer_Release(&point);
        PyBuffer_Release(&scalar);
        return NULL;
    }

    result = PyBytes_FromStringAndSize(NULL, X25519_KEY_LEN);
    if (result != NULL) {
        x25519((uint8_t *)PyBytes_AS_STRING(result), (const uint8_t *)scalar.buf,
            (const uint8_t *)point.buf);
    }
    PyBuffer_Release(&point);
    PyBuffer_Release(&scalar);
    return result;
}

static PyObject *
py_pk_ed25519_to_x25519(PyObject *self, PyObject *args)
{
    Py_buffer in;
    PyObject *result;

    (void)self;
    if (!PyArg_ParseTuple(args, "y*:pk_ed25519_to_x25519", &in)) {
        return NULL;
    }
    if (expect_len(&in, ED25519_KEY_LEN, "in") < 0) {
        PyBuffer_Release(&in);
        return NULL;
    }

    result = PyBytes_FromStringAndSize(NULL, X25519_KEY_LEN);
    if (result != NULL) {
        pk_ed25519_to_x25519((uint8_t *)PyBytes_AS_STRING(result), (const uint8_t *)in.buf);
    }
    PyBuffer_Release(&in);
    return result;
}

static PyObject *
py_sk_ed25519_to_x25519(PyObject *self, PyObject *args)
{
    Py_buffer in;
    PyObject *result;

    (void)self;
    if (!PyArg_ParseTuple(args, "y*:sk_ed25519_to_x25519", &in)) {
        return NULL;
    }
    if (expect_len(&in, ED25519_KEY_LEN, "in") < 0) {
        PyBuffer_Release(&in);
        return NULL;
    }

    result = PyBytes_FromStringAndSize(NULL, X25519_KEY_LEN);
    if (result != NULL) {
        sk_ed25519_to_x25519((uint8_t *)PyBytes_AS_STRING(result), (const uint8_t *)in.buf);
    }
    PyBuffer_Release(&in);
    return result;
}

static PyMethodDef module_methods[] = {
    {"ed25519_genpub", py_ed25519_genpub, METH_VARARGS, PyDoc_STR("Return an Ed25519 public key for a 32-byte secret key.")},
    {"ed25519_sign", py_ed25519_sign, METH_VARARGS, PyDoc_STR("Return a 64-byte Ed25519 signature for sec, pub, and data.")},
    {"ed25519_verify", py_ed25519_verify, METH_VARARGS, PyDoc_STR("Return True if sig verifies for pub and data.")},
    {"x25519_base", py_x25519_base, METH_VARARGS, PyDoc_STR("Return the X25519 public value for a 32-byte scalar.")},
    {"x25519", py_x25519, METH_VARARGS, PyDoc_STR("Return the X25519 shared value for scalar and point.")},
    {"pk_ed25519_to_x25519", py_pk_ed25519_to_x25519, METH_VARARGS, PyDoc_STR("Convert an Ed25519 public key to an X25519 public key.")},
    {"sk_ed25519_to_x25519", py_sk_ed25519_to_x25519, METH_VARARGS, PyDoc_STR("Convert an Ed25519 secret key to an X25519 secret key.")},
    {"eddsa_genpub", py_ed25519_genpub, METH_VARARGS, PyDoc_STR("Obsolete alias for ed25519_genpub.")},
    {"eddsa_sign", py_ed25519_sign, METH_VARARGS, PyDoc_STR("Obsolete alias for ed25519_sign.")},
    {"eddsa_verify", py_ed25519_verify, METH_VARARGS, PyDoc_STR("Obsolete alias for ed25519_verify.")},
    {"DH", py_x25519, METH_VARARGS, PyDoc_STR("Obsolete alias for x25519.")},
    {"eddsa_pk_eddsa_to_dh", py_pk_ed25519_to_x25519, METH_VARARGS, PyDoc_STR("Obsolete alias for pk_ed25519_to_x25519.")},
    {"eddsa_sk_eddsa_to_dh", py_sk_ed25519_to_x25519, METH_VARARGS, PyDoc_STR("Obsolete alias for sk_ed25519_to_x25519.")},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "_eddsa",
    PyDoc_STR("CPython bindings for libeddsa."),
    -1,
    module_methods,
    NULL,
    NULL,
    NULL,
    NULL
};

PYEDDSA_MODINIT_FUNC
PyInit__eddsa(void)
{
    PyObject *module = PyModule_Create(&moduledef);
    if (module == NULL) {
        return NULL;
    }
    if (PyModule_AddIntConstant(module, "ED25519_KEY_LEN", ED25519_KEY_LEN) < 0 ||
        PyModule_AddIntConstant(module, "ED25519_SIG_LEN", ED25519_SIG_LEN) < 0 ||
        PyModule_AddIntConstant(module, "X25519_KEY_LEN", X25519_KEY_LEN) < 0) {
        Py_DECREF(module);
        return NULL;
    }
    return module;
}
