/*
 * XPlane2Blender visual parity plugin (see ../README.md). Once the runner has
 * armed it and the scenery has loaded, it puts the green booth and the model
 * 40 m ahead of the aircraft with the Instance API, feeds the model its dataref
 * values, takes the camera through the views in VIEWS, screenshots each, and
 * quits X-Plane. Files in its own folder:
 *
 *   ARMED      present for one run; removed when read
 *   VIEWS      "FOV deg", then one "cx cy cz tx ty tz" line per view: camera and
 *              target offsets from the model origin, in OBJ coordinates
 *   DATAREFS   "name value" lines, the model's animation datarefs
 *   log.txt    what happened
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "XPLMCamera.h"
#include "XPLMDataAccess.h"
#include "XPLMInstance.h"
#include "XPLMPlugin.h"
#include "XPLMProcessing.h"
#include "XPLMScenery.h"
#include "XPLMUtilities.h"

#define MAX_VIEWS 32
#define MAX_DREFS 16
#define AHEAD_M 40.0
#define PI 3.14159265358979323846

static char g_dir[1024];
static FILE *g_log;
static float g_t, g_state_t, g_armed_t = -1;
static int g_state;
static float g_quiet_since = -1;
static XPLMDataRef g_loading, g_local_x, g_local_y, g_local_z, g_psi, g_fov_ref;

static float g_views[MAX_VIEWS][6];
static int g_nviews, g_view = -1;
static float g_fov = 60.0f;
static char g_dref_names[MAX_DREFS][256];
static const char *g_dref_ptrs[MAX_DREFS + 1];
static float g_dref_vals[MAX_DREFS];
static int g_ndrefs;
static float g_no_vals[1];
static XPLMObjectRef g_booth_obj, g_model_obj;
static XPLMInstanceRef g_booth, g_model;
static double g_px, g_py, g_pz;

static void logf_(const char *fmt, const char *a)
{
    if (!g_log) return;
    fprintf(g_log, "%8.1f ", g_t);
    fprintf(g_log, fmt, a ? a : "");
    fputc('\n', g_log);
    fflush(g_log);
}

static void logn(const char *what, double n)
{
    char msg[64];
    snprintf(msg, sizeof msg, "%.3f", n);
    char fmt[128];
    snprintf(fmt, sizeof fmt, "%s %%s", what);
    logf_(fmt, msg);
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

static int read_views(void)
{
    char p[1100], line[512];
    path_in_dir(p, sizeof p, "VIEWS");
    FILE *f = fopen(p, "r");
    if (!f) { logf_("no VIEWS file", NULL); return 0; }
    g_nviews = 0;
    while (fgets(line, sizeof line, f) && g_nviews < MAX_VIEWS) {
        float v[6];
        if (sscanf(line, "FOV %f", &g_fov) == 1) continue;
        if (sscanf(line, "%f %f %f %f %f %f", &v[0], &v[1], &v[2], &v[3], &v[4], &v[5]) == 6) {
            memcpy(g_views[g_nviews++], v, sizeof v);
        }
    }
    fclose(f);
    logn("views:", g_nviews);
    logn("fov:", g_fov);
    return g_nviews;
}

static void read_datarefs(void)
{
    char p[1100], line[512];
    path_in_dir(p, sizeof p, "DATAREFS");
    g_ndrefs = 0;
    FILE *f = fopen(p, "r");
    if (f) {
        while (fgets(line, sizeof line, f) && g_ndrefs < MAX_DREFS) {
            float v;
            if (sscanf(line, "%255s %f", g_dref_names[g_ndrefs], &v) == 2) {
                g_dref_vals[g_ndrefs] = v;
                g_dref_ptrs[g_ndrefs] = g_dref_names[g_ndrefs];
                logf_("dataref %s", g_dref_names[g_ndrefs]);
                g_ndrefs++;
            }
        }
        fclose(f);
    }
    g_dref_ptrs[g_ndrefs] = NULL;
}

/* The booth and model go AHEAD_M ahead of the aircraft, on the terrain */
static int setup_scene(void)
{
    double ax = XPLMGetDatad(g_local_x), ay = XPLMGetDatad(g_local_y), az = XPLMGetDatad(g_local_z);
    double psi = XPLMGetDataf(g_psi) * PI / 180.0;
    g_px = ax + sin(psi) * AHEAD_M;
    g_pz = az - cos(psi) * AHEAD_M;
    g_py = ay;
    XPLMProbeRef probe = XPLMCreateProbe(xplm_ProbeY);
    XPLMProbeInfo_t info;
    memset(&info, 0, sizeof info);
    info.structSize = sizeof info;
    if (XPLMProbeTerrainXYZ(probe, (float)g_px, (float)(g_py + 200.0), (float)g_pz, &info) == xplm_ProbeHitTerrain) {
        g_py = info.locationY;
    } else {
        logf_("terrain probe missed, using the aircraft's height", NULL);
    }
    /* Above the terrain, so that sloping ground doesn't come up through the booth floor
     * away from the origin; the views are relative to the origin, so height doesn't matter */
    g_py += 1.0;
    XPLMDestroyProbe(probe);
    logn("model x:", g_px);
    logn("model y:", g_py);
    logn("model z:", g_pz);

    g_booth_obj = XPLMLoadObject("Resources/plugins/xp2b_parity/objects/booth.obj");
    g_model_obj = XPLMLoadObject("Resources/plugins/xp2b_parity/objects/model.obj");
    if (!g_booth_obj || !g_model_obj) {
        logf_(g_booth_obj ? "model.obj did not load" : "booth.obj did not load", NULL);
        return 0;
    }
    g_booth = XPLMCreateInstance(g_booth_obj, g_dref_ptrs + g_ndrefs); /* an empty, NULL-terminated list */
    g_model = XPLMCreateInstance(g_model_obj, g_dref_ptrs);
    if (!g_booth || !g_model) { logf_("instances could not be created", NULL); return 0; }
    if (g_fov_ref) XPLMSetDataf(g_fov_ref, g_fov);
    return 1;
}

static void place_instances(void)
{
    XPLMDrawInfo_t pos;
    memset(&pos, 0, sizeof pos);
    pos.structSize = sizeof pos;
    pos.x = (float)g_px;
    pos.y = (float)g_py;
    pos.z = (float)g_pz;
    if (g_booth) XPLMInstanceSetPosition(g_booth, &pos, g_no_vals);
    if (g_model) XPLMInstanceSetPosition(g_model, &pos, g_dref_vals);
}

static int camera_cb(XPLMCameraPosition_t *out, int losing_control, void *ref)
{
    if (losing_control || g_view < 0 || g_view >= g_nviews) return 0;
    const float *v = g_views[g_view];
    double cx = g_px + v[0], cy = g_py + v[1], cz = g_pz + v[2];
    double dx = (g_px + v[3]) - cx, dy = (g_py + v[4]) - cy, dz = (g_pz + v[5]) - cz;
    out->x = (float)cx;
    out->y = (float)cy;
    out->z = (float)cz;
    /* X-Plane local: +X east, +Y up, -Z north; heading clockwise from north */
    out->heading = (float)(atan2(dx, -dz) * 180.0 / PI);
    out->pitch = (float)(atan2(dy, sqrt(dx * dx + dz * dz)) * 180.0 / PI);
    out->roll = 0.0f;
    out->zoom = 1.0f;
    return 1;
}

static float loop_cb(float since_call, float since_loop, int counter, void *ref)
{
    g_t += since_call;
    float in_state = g_t - g_state_t;
#define NEXT(s) do { g_state = (s); g_state_t = g_t; } while (0)

    if (g_booth || g_model) place_instances();

    /* Flight loops don't run while X-Plane loads or shows a dialog, so the first call can
     * arrive minutes in; the timeout counts from arming, not from start */
    if (g_armed_t >= 0 && g_t - g_armed_t > 420.0f && g_state > 0 && g_state < 90) {
        logf_("TIMEOUT, quitting", NULL);
        NEXT(90);
    }

    switch (g_state) {
    case 0: /* let the sim settle in the flight it started with */
        if (in_state > 5.0f) {
            char p[1100];
            path_in_dir(p, sizeof p, "ARMED");
            FILE *armed = fopen(p, "rb");
            if (!armed) { logf_("not armed, doing nothing", NULL); NEXT(99); break; }
            fclose(armed);
            remove(p);
            g_armed_t = g_t;
            logf_("armed", NULL);
            NEXT(1);
        }
        break;
    case 1: /* wait for scenery to finish loading: quiet for 10 s, at least 40 s in */
    {
        int loading = g_loading ? XPLMGetDatai(g_loading) : 0;
        if (loading) g_quiet_since = -1;
        else if (g_quiet_since < 0) g_quiet_since = g_t;
        if (in_state > 40.0f && g_quiet_since >= 0 && g_t - g_quiet_since > 10.0f) {
            logf_("scenery loaded", NULL);
            if (!read_views()) { NEXT(90); break; }
            read_datarefs();
            if (!setup_scene()) { NEXT(90); break; }
            run_command("sim/view/forward_with_nothing");
            g_view = 0;
            XPLMControlCamera(xplm_ControlCameraForever, camera_cb, NULL);
            logf_("camera taken, first view", NULL);
            NEXT(2);
        }
        break;
    }
    case 2: /* hold the view, long enough for auto-exposure the first time, then shoot */
        if (in_state > (g_view == 0 ? 20.0f : 4.0f)) {
            logn("screenshot of view", g_view);
            run_command("sim/operation/screenshot");
            NEXT(3);
        }
        break;
    case 3: /* give the screenshot its own second in the file name */
        if (in_state > 2.5f) {
            g_view++;
            if (g_view >= g_nviews) NEXT(90);
            else NEXT(2);
        }
        break;
    case 90:
        logf_("quitting", NULL);
        XPLMDontControlCamera();
        run_command("sim/operation/quit");
        NEXT(91);
        break;
    default:
        break;
    }
    return -1.0f;
}

PLUGIN_API int XPluginStart(char *name, char *sig, char *desc)
{
    strcpy(name, "XP2B visual parity");
    strcpy(sig, "xplane2blender.test.parity");
    strcpy(desc, "Places an OBJ in a green booth and screenshots it from set views");
    XPLMEnableFeature("XPLM_USE_NATIVE_PATHS", 1);

    char path[1024];
    XPLMGetPluginInfo(XPLMGetMyID(), NULL, path, NULL, NULL);
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
    if (g_model) XPLMDestroyInstance(g_model);
    if (g_booth) XPLMDestroyInstance(g_booth);
    if (g_model_obj) XPLMUnloadObject(g_model_obj);
    if (g_booth_obj) XPLMUnloadObject(g_booth_obj);
    logf_("stopped", NULL);
    if (g_log) fclose(g_log);
}

PLUGIN_API int XPluginEnable(void)
{
    g_loading = XPLMFindDataRef("sim/graphics/scenery/async_scenery_load_in_progress");
    g_local_x = XPLMFindDataRef("sim/flightmodel/position/local_x");
    g_local_y = XPLMFindDataRef("sim/flightmodel/position/local_y");
    g_local_z = XPLMFindDataRef("sim/flightmodel/position/local_z");
    g_psi = XPLMFindDataRef("sim/flightmodel/position/psi");
    g_fov_ref = XPLMFindDataRef("sim/graphics/view/field_of_view_deg");
    logf_("enabled", NULL);
    XPLMRegisterFlightLoopCallback(loop_cb, 1.0f, NULL);
    return 1;
}

PLUGIN_API void XPluginDisable(void)
{
    XPLMUnregisterFlightLoopCallback(loop_cb, NULL);
}

PLUGIN_API void XPluginReceiveMessage(XPLMPluginID from, int msg, void *param)
{
}
