#define _XOPEN_SOURCE 700
#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <ucontext.h>

typedef int trigger;
typedef double fixed;
#define null 0
enum state { UNUSED, ACTIVE, WAITING, DONE };
struct task {
    ucontext_t stack_context;
    ucontext_t *caller;
    unsigned char stack[65536];
    enum state state;
    int deadline;
};
static ucontext_t main_context;
static struct task tasks[20];
static int now, current=-1, count, allocated, events, ids[22], ticks[22];
static bool nested_ordinary;
static int libGame_gv_capturePointCurrentCount=7, libCore_gv_cOMPUTER_Neutral=0, c_timeGame=1;
struct capture { bool lv_enabled; int lv_captureBeaconUnit, owner; };
static struct capture libGame_gv_capturePoints[8];
static trigger TriggerCreate(const char *name);
static void TriggerExecute(trigger handle, bool conditions, bool wait);
static void Wait(fixed delay, int clock);
static void ActorSend(int actor, const char *signal);
static void UnitSetOwner(int unit,int owner,bool change);
static int libNtve_gf_MainActorofUnit(int unit) { return unit; }
#include "emitted.h"

static trigger TriggerCreate(const char *name) {
    assert(!strcmp(name,"gt_HistoricalCapturePointDisable") && !allocated);
    return ++allocated;
}
static void enter(void) {
    int id=current;
    assert(gt_HistoricalCapturePointDisable(false,true));
    tasks[id].state=DONE;
    assert(!swapcontext(&tasks[id].stack_context,tasks[id].caller));
    abort();
}
static void resume(int id) {
    int parent=current;
    ucontext_t *caller=parent<0 ? &main_context : &tasks[parent].stack_context;
    current=id;
    tasks[id].caller=caller;
    tasks[id].state=ACTIVE;
    assert(!swapcontext(caller,&tasks[id].stack_context));
    assert(tasks[id].state==DONE || tasks[id].state==WAITING);
    current=parent;
}
static void TriggerExecute(trigger handle,bool conditions,bool wait) {
    assert(handle==1 && !conditions && !wait && count<20);
    int id=count++;
    assert(!getcontext(&tasks[id].stack_context));
    tasks[id].stack_context.uc_stack.ss_sp=tasks[id].stack;
    tasks[id].stack_context.uc_stack.ss_size=sizeof(tasks[id].stack);
    tasks[id].stack_context.uc_stack.ss_flags=0;
    tasks[id].stack_context.uc_link=NULL;
    makecontext(&tasks[id].stack_context,enter,0);
    resume(id);
}
static void Wait(fixed delay,int clock) {
    int id=current;
    assert(clock==1 && tasks[id].state==ACTIVE);
    tasks[id].deadline=now+(int)(16*delay);
    tasks[id].state=WAITING;
    assert(!swapcontext(&tasks[id].stack_context,tasks[id].caller));
    assert(current==id && tasks[id].state==ACTIVE && now==tasks[id].deadline);
}
static void advance(int tick) {
    assert(tick>=now);
    now=tick;
    for (int id=count-1;id>=0;id--) {
        if (tasks[id].state==WAITING && tasks[id].deadline<=tick) resume(id);
    }
}
static void ActorSend(int actor,const char *signal) {
    assert(actor>=101 && actor<=107 && !strcmp(signal,"Signal Hide"));
    if (nested_ordinary && actor==106) {
        nested_ordinary=false;
        libGame_gf_CapturePointDisable(2);
    }
}
static void UnitSetOwner(int unit,int owner,bool change) {
    assert(unit>=101 && unit<=107 && owner==0 && change);
    ids[events]=unit;
    ticks[events++]=now;
    libGame_gv_capturePoints[unit-100].owner=owner;
}
int main(void) {
    for (int i=1;i<=7;i++) libGame_gv_capturePoints[i]=(struct capture){true,100+i,12};
    for (int i=1;i<=5;i++) gf_HistoricalFirstCampDisable(i);
    libGame_gf_CapturePointDisable(6);
    libGame_gf_CapturePointDisable(7);
    assert(allocated==1 && count==7 && events==0);
    advance(47);
    assert(events==0);
    advance(48);
    assert(events==7);
    for (int i=0;i<7;i++) assert(ids[i]==107-i && ticks[i]==48);

    advance(2514);
    for (int i=1;i<=7;i++) libGame_gv_capturePoints[i]=(struct capture){true,100+i,12};
    nested_ordinary=true;
    extracted_dragon_call(6);
    extracted_dragon_call(7);
    extracted_dragon_call(7);
    extracted_dragon_call(8);
    libGame_gf_CapturePointDisable(3);
    assert(!gv_HistoricalDragonDisablePending && !nested_ordinary && allocated==1 && count==13);
    advance(2529);
    assert(events==7 && libGame_gv_capturePoints[6].owner==12 && libGame_gv_capturePoints[7].owner==12);
    advance(2530);
    assert(events==9 && ids[7]==107 && ids[8]==106 && ticks[7]==2530 && ticks[8]==2530);
    assert(libGame_gv_capturePoints[2].owner==12 && libGame_gv_capturePoints[3].owner==12);
    advance(2561);
    assert(events==9);
    advance(2562);
    assert(events==11 && ids[9]==103 && ids[10]==102 && ticks[9]==2562 && ticks[10]==2562);
    assert(libGame_gv_capturePoints[2].owner==0 && libGame_gv_capturePoints[3].owner==0);
    return 0;
}
