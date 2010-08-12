what = '''
import core
core.start()
'''
print 'profiling...'
import cProfile
p = cProfile.Profile()
p.run(what)
stats = p.getstats()
print "BY CALLS:\n------------------------------------------------------------"
def c(x, y):
    if x.callcount < y.callcount:
        return 1
    elif x.callcount == y.callcount:
        return 0
    else:
        return -1
stats.sort(cmp = c)
for line in stats[:100]:
    print "%d %4f %s" % (line.callcount, line.totaltime, line.code)
    if line.calls == None:
        continue
    line.calls.sort(cmp = c)
    for line in line.calls[:10]:
        print "-- %d %4f %s" % (line.callcount, line.totaltime, line.code)


print "BY TOTALTIME:\n------------------------------------------------------------"
def c(x, y):
    if x.totaltime < y.totaltime:
        return 1
    elif x.totaltime == y.totaltime:
        return 0
    else:
        return -1
stats.sort(cmp = c)
for line in stats[:30]:
    print "%d %4f %s" % (line.callcount, line.totaltime, line.code)
    if line.calls == None:
        continue
    line.calls.sort(cmp = c)
    for line in line.calls[:10]:
        print "-- %d %4f %s" % (line.callcount, line.totaltime, line.code)