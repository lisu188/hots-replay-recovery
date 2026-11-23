/* The verifier inserts three functions from the generated map here. The mock
 * timer records requests; it never executes the game or schedules callbacks. */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

typedef int unit;
enum { null = 0, c_timeGame = 1 };
struct Camp {
    bool lv_stateIsEnabled;
    unit lv_campIconUnit;
    int lv_stateCreepBirthTimer;
    int lv_stateCreepRespawnTimer;
};
static struct Camp libMapM_gv_jungleCreepCamps[6];
static int libMapM_gv_jungleNumberOfCreepCamps;
static bool gv_HistoricalCampOpeningPending, libCore_gv_sYSJungleCreepCamps;
static const double libMapM_gv_bALJungleBirthDelay = 3.0;
static int current_timer, timer_calls, opened, delegated;
static bool last_test, last_actions;
static const int flags[] = {0, 477, 479, 478, 480, 476};

static unit UnitFromId(int id) { return id; }
static int EventTimer(void) { return current_timer; }
static void TimerStart(int timer, double seconds, bool periodic, int clock) {
    int camp = timer_calls / 2 + 1;
    assert(camp <= 5 && !periodic && clock == c_timeGame);
    assert(timer == ((timer_calls % 2) ? 200 : 100) + camp);
    assert(seconds == ((timer_calls % 2) ? 123.0 : 120.0));
    ++timer_calls;
}
static void gf_OpenHistoricalCamp(int camp) {
    assert(!gv_HistoricalCampOpeningPending && camp == opened + 1);
    libMapM_gv_jungleCreepCamps[camp].lv_stateIsEnabled = true;
    libMapM_gv_jungleCreepCamps[camp].lv_campIconUnit = 1000 + camp;
    ++opened;
}
static bool libMapM_gt_JungleCreepCampRespawnTimerExpires_Func(bool test, bool actions) {
    ++delegated;
    last_test = test;
    last_actions = actions;
    return !test || libCore_gv_sYSJungleCreepCamps;
}

/* EMITTED FUNCTIONS */

static void reset(void) {
    memset(libMapM_gv_jungleCreepCamps, 0, sizeof(libMapM_gv_jungleCreepCamps));
    libCore_gv_sYSJungleCreepCamps = true;
    libMapM_gv_jungleNumberOfCreepCamps = 5;
    gv_HistoricalCampOpeningPending = false;
    timer_calls = opened = delegated = current_timer = 0;
    for (int i=1; i<=5; ++i) {
        libMapM_gv_jungleCreepCamps[i].lv_stateCreepBirthTimer = 100+i;
        libMapM_gv_jungleCreepCamps[i].lv_stateCreepRespawnTimer = 200+i;
    }
}

static void check_callback(int timer, bool test, bool actions) {
    int previous = delegated;
    current_timer = timer;
    bool actual = gt_HistoricalCampBirthTimer_Func(test, actions);
    assert(delegated == previous + 1 && last_test == test && last_actions == actions);
    assert(actual == (!test || libCore_gv_sYSJungleCreepCamps));
}

int main(void) {
    for (int i=1; i<=5; ++i) assert(gf_HistoricalCampFlag(i) == flags[i]);
    assert(!gf_HistoricalCampFlag(0) && !gf_HistoricalCampFlag(6));
    for (int i=1; i<=5; ++i) {
        reset();
        gf_ScheduleHistoricalCampOpening();
        assert(timer_calls == 10 && gv_HistoricalCampOpeningPending);
        check_callback(100+i, true, false);
        check_callback(200+i, false, true);
        assert(gv_HistoricalCampOpeningPending && !opened);
        libCore_gv_sYSJungleCreepCamps = false;
        check_callback(100+i, true, true);
        assert(gv_HistoricalCampOpeningPending && !opened);
        libCore_gv_sYSJungleCreepCamps = true;
        check_callback(100+i, true, true);
        assert(opened == 5 && !gv_HistoricalCampOpeningPending);
        for (int next=5; next>=1; --next) check_callback(100+next, true, true);
        assert(opened == 5 && delegated == 9);
        gf_ScheduleHistoricalCampOpening();
        assert(timer_calls == 10 && !gv_HistoricalCampOpeningPending);
    }
    for (int failure=0; failure<12; ++failure) {
        reset();
        if (failure == 0) libCore_gv_sYSJungleCreepCamps = false;
        else if (failure == 1) libMapM_gv_jungleNumberOfCreepCamps = 4;
        else if (failure < 7) libMapM_gv_jungleCreepCamps[failure-1].lv_stateIsEnabled = true;
        else libMapM_gv_jungleCreepCamps[failure-6].lv_campIconUnit = 1;
        gf_ScheduleHistoricalCampOpening();
        assert(!timer_calls && !gv_HistoricalCampOpeningPending);
        check_callback(101, false, true);
        assert(!opened);
    }
    puts("{\"first_expiry_permutations\":5,\"rejected_scheduling_states\":12,\"flag_lookup_cases\":7}");
    return 0;
}
