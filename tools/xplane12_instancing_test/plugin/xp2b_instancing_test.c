/*
 * Temporary test plugin for XPlane2Blender: measures whether test OBJs are
 * drawn instanced in X-Plane 12. Reads flight.json from its own folder,
 * starts that flight, waits for scenery, dumps every scalar numeric dataref,
 * takes a screenshot and quits X-Plane. Writes log.txt and datarefs.tsv.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "XPLMPlugin.h"
#include "XPLMProcessing.h"
#include "XPLMDataAccess.h"
#include "XPLMPlanes.h"
#include "XPLMUtilities.h"

static char g_dir[1024];
static FILE *g_log;
static float g_t;          /* seconds since enable */
static int g_state;
static float g_state_t;    /* time when the current state started */
static float g_quiet_since = -1;
static XPLMDataRef g_loading;
static int g_samples;

static void logf_(const char *fmt, const char *a)
{
    if (!g_log) return;
    fprintf(g_log, "%8.1f ", g_t);
    fprintf(g_log, fmt, a ? a : "");
    fputc('\n', g_log);
    fflush(g_log);
}

static void path_in_dir(char *out, size_t n, const char *name)
{
    snprintf(out, n, "%s%s", g_dir, name);
}

static void run_command(const char *name)
{
    XPLMCommandRef c = XPLMFindCommand(name);
    logf_(c ? "command %s" : "command %s NOT FOUND", name);
    if (c) XPLMCommandOnce(c);
}

/* Appends one sample of every scalar int/float/double dataref */
static void dump_datarefs(const char *label)
{
    char p[1100];
    path_in_dir(p, sizeof p, "datarefs.tsv");
    FILE *f = fopen(p, "a");
    if (!f) return;
    int n = XPLMCountDataRefs();
    XPLMDataRef *refs = (XPLMDataRef *)malloc(sizeof(XPLMDataRef) * n);
    XPLMGetDataRefsByIndex(0, n, refs);
    int written = 0;
    for (int i = 0; i < n; i++) {
        XPLMDataRefInfo_t info;
        memset(&info, 0, sizeof info);
        info.structSize = sizeof info;
        XPLMGetDataRefInfo(refs[i], &info);
        if (!info.name) continue;
        XPLMDataTypeID t = info.type;
        double v;
        if (t & xplmType_Double) v = XPLMGetDatad(refs[i]);
        else if (t & xplmType_Float) v = XPLMGetDataf(refs[i]);
        else if (t & xplmType_Int) v = XPLMGetDatai(refs[i]);
        else continue;
        fprintf(f, "%s\t%s\t%.6g\n", label, info.name, v);
        written++;
    }
    free(refs);
    fclose(f);
    char msg[64];
    snprintf(msg, sizeof msg, "%d of %d", written, n);
    logf_("dumped datarefs: %s", msg);
}

static float loop_cb(float since_call, float since_loop, int counter, void *ref)
{
    g_t += since_call;
    float in_state = g_t - g_state_t;
#define NEXT(s) do { g_state = (s); g_state_t = g_t; } while (0)

    if (g_t > 300.0f && g_state > 0 && g_state < 90) {
        logf_("TIMEOUT, quitting", NULL);
        NEXT(90);
    }

    switch (g_state) {
    case 0: /* let the sim settle in the flight it started with */
        if (in_state > 5.0f) {
            char p[1100];
            /* Only act when the test runner armed us; one run per arming */
            path_in_dir(p, sizeof p, "ARMED");
            FILE *armed = fopen(p, "rb");
            if (!armed) { logf_("not armed, doing nothing", NULL); NEXT(99); break; }
            fclose(armed);
            remove(p);
            /* The test runner started this flight through X-Plane's Web API */
            logf_("armed, flight running", NULL);
            NEXT(1);
        }
        break;
    case 1: /* wait for scenery to finish loading, quiet for 10 s, at least 40 s */
    {
        int loading = g_loading ? XPLMGetDatai(g_loading) : 0;
        if (loading) g_quiet_since = -1;
        else if (g_quiet_since < 0) g_quiet_since = g_t;
        if (in_state > 40.0f && g_quiet_since >= 0 && g_t - g_quiet_since > 10.0f) {
            logf_("scenery loaded", NULL);
            run_command("sim/view/forward_with_nothing");
            NEXT(2);
        }
        break;
    }
    case 2: /* sample the datarefs 5 times, a second apart */
        if (in_state > 5.0f + g_samples) {
            char label[16];
            snprintf(label, sizeof label, "s%d", g_samples);
            dump_datarefs(label);
            if (++g_samples >= 5) NEXT(3);
        }
        break;
    case 3: /* let auto-exposure settle before the screenshot */
        if (in_state > 20.0f) {
            run_command("sim/operation/screenshot");
            NEXT(4);
        }
        break;
    case 4:
        if (in_state > 4.0f) NEXT(90);
        break;
    case 90:
        logf_("quitting", NULL);
        run_command("sim/operation/quit");
        NEXT(91);
        break;
    default:
        break;
    }
    return -1.0f; /* every frame */
}

PLUGIN_API int XPluginStart(char *name, char *sig, char *desc)
{
    strcpy(name, "XP2B instancing test");
    strcpy(sig, "xplane2blender.test.instancing");
    strcpy(desc, "Temporary test plugin for XPlane2Blender instancing validation");
    XPLMEnableFeature("XPLM_USE_NATIVE_PATHS", 1);

    char path[1024];
    XPLMGetPluginInfo(XPLMGetMyID(), NULL, path, NULL, NULL);
    /* path is <dir>/64/win.xpl, with mixed / and \ separators; results go in <dir> */
    strcpy(g_dir, path);
    for (int up = 0; up < 2; up++) {
        char *a = strrchr(g_dir, '\\'), *b = strrchr(g_dir, '/');
        char *s = a > b ? a : b;
        if (s) *s = 0;
    }
    strcat(g_dir, "\\");
    char p[1100];
    path_in_dir(p, sizeof p, "log.txt");
    g_log = fopen(p, "w");
    logf_("started, dir %s", g_dir);
    return 1;
}

PLUGIN_API void XPluginStop(void)
{
    logf_("stopped", NULL);
    if (g_log) fclose(g_log);
}

PLUGIN_API int XPluginEnable(void)
{
    g_loading = XPLMFindDataRef("sim/graphics/scenery/async_scenery_load_in_progress");
    logf_(g_loading ? "enabled (%s)" : "enabled, no load-progress dataref%s", "");
    XPLMRegisterFlightLoopCallback(loop_cb, 1.0f, NULL);
    return 1;
}

PLUGIN_API void XPluginDisable(void)
{
    XPLMUnregisterFlightLoopCallback(loop_cb, NULL);
}

PLUGIN_API void XPluginReceiveMessage(XPLMPluginID from, int msg, void *param)
{
    char m[32];
    snprintf(m, sizeof m, "%d", msg);
    logf_("message %s", m);
}
