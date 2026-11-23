#define _XOPEN_SOURCE 700
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ucontext.h>

typedef int unit, trigger, playergroup;
typedef double fixed;
typedef const char *string;
#define null 0
#define c_timeGame 1
static const int libCore_gv_cOMPUTER_TeamOrder=11, libCore_gv_cOMPUTER_TeamChaos=12;
static const int libCore_gv_cOMPUTER_Hostile=15, libCore_gv_oBSERVER_ObserverUIPlayer=0;
static const int libMapM_gv_jungleNumberOfCreepCamps=5;
static struct camp {
    int lv_captureCapturePointIndex, lv_mapDataDefenderLeashRegion, lv_campIconUnit;
    int lv_campOwnershipFlagUnit, lv_captureCircleOfPowerUnit, lv_capturingPlayer;
    bool lv_captureCaptureEnabled;
} libMapM_gv_jungleCreepCamps[6];
static struct { struct { struct { string lv_bannerID; } lv_loot_Banner; } lv_lootContent; } libGame_gv_players[16];
static int now, index_arg, owner_arg, ceded, credited_camp, credits, draws;
static int libGame_gv_capturePointCurrentCount=7, libCore_gv_cOMPUTER_Neutral=0;
static struct {bool lv_enabled; unit lv_captureBeaconUnit;} libGame_gv_capturePoints[8];
static int owner[800], owner_ids[32], owner_ticks[32], owners, actor_resets, banners, sounds, tags, snapshots;
static int created, capture_handle_count, old_dispatch, next_task, current, banner_tasks;
static struct thread {
    ucontext_t context;
    unsigned char stack[65536];
    int deadline;
    bool waiting;
    bool capture;
} tasks[12];
static ucontext_t caller;
static int UnitFromId(int id) { return id; }
static int libGame_gf_CapturePointChangesOwnerCapturePointIndex(void) { return index_arg; }
static int libGame_gf_CapturePointChangesOwnerOwner(void) { return owner_arg; }
static bool libGame_gf_CapturePointChangesOwnerHasMercLordTalent(void) { return owner_arg==12; }
#define libGame_gf_CapturePointChangesOwnerCapturingPlayers() 2
static void libGame_gf_SendEventMercCampCaptured(int c,int o,int p) { assert(p==2 && o==owner_arg); ceded=c; }
#define libNtve_gf_SendActorMessageToGameRegion(...) ((void)0)
#define libGame_gf_TeamNumberOfPlayer(p) ((p)-10)
#define SoundPlayForPlayer(...) (++sounds)
static void ActorSend(int actor,string signal) { assert(actor>=101 && actor<=107 && !strcmp(signal,"Signal Hide")); }
static void gf_HistoricalMercRewards(int c,int o,bool talent) {
    assert(c==ceded && o==owner_arg && talent==(o==12)); credited_camp=c; ++credits;
}
static void UnitSetOwner(int u,int o,bool change) {
    assert(u>=0 && u<800 && change && owners<32);
    owner[u]=o; owner_ticks[owners]=now; owner_ids[owners++]=u;
}
static int PlayerGroupCount(int group) { return group; }
static int RandomInt(int first,int last) { assert(first==1 && last>=1); ++draws; return last; }
static int PlayerGroupPlayer(int group,int position) { assert(group==position); return position; }
static void libNtve_gf_SendActorMessageToUnit(int u,string msg) { assert(u>=0 && !strcmp(msg,"Signal ResetBanner")); ++actor_resets; }
static int libNtve_gf_MainActorofUnit(int u) { return u; }
static string libNtve_gf_BannerSet(string b) { assert(b); return b; }
static void ActorSendTo(int u,string target,string b) { assert(u>=0 && b && !strcmp(target,"LootBanner")); ++banners; }
#define TextTagDestroy(...) ((void)0)
#define TextExpressionSetToken(...) ((void)0)
#define TextTagCreate(...) (++tags)
#define TextTagAttachToUnit(...) ((void)0)
#define libCore_gf_StoreTextTagForUnit(...) ((void)0)
#define libMapM_gf_CreateSnapshotOfUnitForBothTeams(...) (++snapshots)
static void Wait(double delay,int clock);
static void TriggerExecute(trigger h,bool cond,bool wait);
static trigger TriggerCreate(string name) {
    if (!strcmp(name,"gt_HistoricalMercBanner")) { ++created; return 23; }
    assert(!strcmp(name,"gt_HistoricalCapturePointDisable") && !capture_handle_count);
    ++capture_handle_count;
    return 17;
}
#include "emitted.h"

static void wait_worker(void) {
    if (tasks[current].capture) assert(gt_HistoricalCapturePointDisable(false,true));
    else assert(gt_HistoricalMercBanner(false,true));
    tasks[current].waiting=false;
}
static void Wait(double delay,int clock) {
    struct thread *t=&tasks[current];
    assert(clock==1 && (delay==0.5 || delay==1.0 || delay==1.5 || delay==3.0));
    t->deadline=now+(int)(16*delay); t->waiting=true;
    assert(!swapcontext(&t->context,&caller));
    assert(t->deadline==now);
}
static void TriggerExecute(trigger h,bool cond,bool wait) {
    assert(!cond && !wait);
    if (h==11) { ++old_dispatch; return; }
    assert((h==23 || h==17) && next_task<12);
    current=next_task++;
    struct thread *t=&tasks[current];
    t->capture=h==17;
    if (!t->capture) ++banner_tasks;
    assert(!getcontext(&t->context));
    t->context.uc_stack.ss_sp=t->stack; t->context.uc_stack.ss_size=sizeof(t->stack);
    t->context.uc_link=&caller;
    makecontext(&t->context,wait_worker,0);
    assert(!swapcontext(&caller,&t->context));
}
static void advance(int loop) {
    now=loop;
    for (int i=next_task-1;i>=0;i--) {
        if (tasks[i].waiting && tasks[i].deadline==now) {
            current=i;
            assert(!swapcontext(&caller,&tasks[i].context));
        }
    }
}

int main(void) {
    for (int i=1;i<=5;i++) libMapM_gv_jungleCreepCamps[i]=(struct camp){i,200+i,300+i,gf_HistoricalCampFlag(i),100+i,0,true};
    for (int i=1;i<=7;i++) {
        libGame_gv_capturePoints[i].lv_enabled=true;
        libGame_gv_capturePoints[i].lv_captureBeaconUnit=100+i;
    }
    gf_HistoricalFirstCampDisable(3);
    assert(capture_handle_count==1 && tasks[0].deadline==48);
    index_arg=2; owner_arg=11;
    assert(gt_HistoricalMercOwnership(false,false) && !ceded);
    index_arg=7;
    assert(gt_HistoricalMercOwnership(false,true) && !ceded);
    index_arg=2; owner_arg=0;
    assert(gt_HistoricalMercOwnership(false,true) && ceded==2 && credits==0 && owners==0);
    for (int i=1;i<=2;i++) {
        index_arg=i; owner_arg=10+i;
        assert(gt_HistoricalMercOwnership(false,true) && credited_camp==i);
        assert(tasks[i].capture && tasks[i].waiting && tasks[i].deadline==16);
        int offset=(i-1)*3;
        assert(owner_ids[offset]==300+i && owner_ids[offset+1]==gf_HistoricalCampFlag(i) && owner_ids[offset+2]==100+i);
        assert(owner[gf_HistoricalCampFlag(i)]==owner_arg && !libMapM_gv_jungleCreepCamps[i].lv_captureCaptureEnabled);
    }
    assert(credits==2 && sounds==6);
    gf_HistoricalMercBannerCredit(1,0);
    assert(!draws && !created);
    gf_HistoricalMercBannerCredit(1,4);
    gf_HistoricalMercBannerCredit(2,6);
    gf_HistoricalMercBanner(550,"Normal",3,false);
    gf_HistoricalMercBanner(gf_HistoricalCampFlag(3),"Tagged",5,true);
    assert(draws==2 && libMapM_gv_jungleCreepCamps[1].lv_capturingPlayer==4 && libMapM_gv_jungleCreepCamps[2].lv_capturingPlayer==6);
    assert(created==1 && auto_libGame_gf_DropLootBannerinSconce_Trigger==23 && gv_HistoricalMercBannerTrigger==23);
    advance(7);
    assert(owners==6 && banners==0);
    advance(8);
    assert(owners==8 && banners==4 && actor_resets==4 && tags==2 && !snapshots);
    assert(owner[gf_HistoricalCampFlag(1)]==11 && owner[gf_HistoricalCampFlag(2)]==12 && owner[550]==3 && owner[gf_HistoricalCampFlag(3)]==5);
    assert(owner_ticks[6]==8 && owner_ticks[7]==8);
    // Simulate an unrelated ordinary caller acquiring the stock slot before the scoped entry.
    gv_HistoricalMercBannerTrigger=0; auto_libGame_gf_DropLootBannerinSconce_Trigger=11;
    gf_HistoricalMercBanner(550,"Normal",4,false);
    assert(created==1 && old_dispatch==1 && !gv_HistoricalMercBannerTrigger);
    gf_HistoricalMercBannerCredit(1,2);
    assert(created==2 && old_dispatch==1 && gv_HistoricalMercBannerTrigger==23 && auto_libGame_gf_DropLootBannerinSconce_Trigger==11);
    advance(16);
    assert(owners==10 && owner[gf_HistoricalCampFlag(1)]==11 && draws==3 && banners==5);
    assert(owner_ids[8]==102 && owner_ids[9]==101 && owner_ticks[8]==16 && owner_ticks[9]==16);
    advance(47);
    assert(owners==10);
    advance(48);
    assert(owners==11 && owner_ids[10]==103 && owner_ticks[10]==48 && capture_handle_count==1);
    printf("{\"capture_team_branches\":%d,\"banner_tasks_completed\":%d,\"credit_rng_draws\":%d,\"ordinary_prebound_delegations\":%d,\"shared_capture_handle\":%d}\n",
           credits,banner_tasks,draws,old_dispatch,capture_handle_count);
    return 0;
}
