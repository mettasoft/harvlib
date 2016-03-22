import sys, getopt
from pprint import pprint
import datetime
import harvest

# functions for interacting with data obtained via the harvest.py API


class TimeSummary(object):
    """ collect the details of a particular date+project+userfor summary to Gavel """
    def __init__(self, date, project, user):
        self.date = date
        self.project = project
        self.user = user
        self.key  = "%s:%s:%s" % (date,project.code,user.username)
        self.data = list()
        self.hours = 0.0
        self.text = list()

    def __cmp__(self, other):
        return self.key.__cmp__(other.key)


    def add_entry(self, entry):
        # danger - all entries should be on the same date!
        pprint(entry)
        assert(entry['day_entry']['spent_at'] == self.date) 
        self.hours += float(entry['day_entry']['hours'])
        text = entry['day_entry']['notes'].replace("\n",". ")
        self.text.append(text)
        self.data.append(entry)
        
    def __repr__(self):
        return "TimeSummary(%s,%s,%s) - %s hours, %s items, %s" % (self.date, self.project.code, self.user.username, self.hours, len(self.text), ";".join(self.text))

    def to_tsv_record(self):
        return "%s\t%s\t%s\t%s\t%s\t%s\n" % (self.date, self.project.code, self.user.username, self.hours, ";".join(self.text), len(self.text))


class TimeUser(object):
    def __init__(self, data):
        pprint(data)
        self.username = data['user']['email'].split("@")[0]
        self.project_id = data['user']['id']
        self.data = data


class TimeProject(object):
    def __init__(self, data):
        pprint(data)
        self.code = data['project']['code']
        self.project_id = data['project']['id']
        self.data = data


def get_client_by_name(svc, name):
    ll = [ c for c in svc.clients() if c['client']['name'] == name ]
    return ll[0] if len(ll) == 1 else None


USERS = {}

def get_user(svc, user_id):

    if not USERS.has_key(user_id):
        udata = svc.get_person(user_id)
        USERS[user_id] = TimeUser(udata)

    user = USERS[user_id]
    #pprint(user)
    return user

PROJECTS = {}

def get_project(svc, project_id):

    if not PROJECTS.has_key(project_id):
        project = svc.get_project(project_id)
        PROJECTS[project_id] = TimeProject(project)

    project = PROJECTS[project_id]
    #pprint(project)
    return project

SUMMARIES = {}
def get_summary(date,project,user):
    summary_key = "%s:%s:%s" % (date,project.code,user.username)
    if not SUMMARIES.has_key(summary_key):
        summary = TimeSummary(date,project,user)
        SUMMARIES[summary_key] = summary

    return SUMMARIES[summary_key]



#-- DATE functions --

def get_dates_for_week_ending(d):
    """ 
    Example:
    date('2016-01-01)  -> [ date('2015-12-27'), 
                                date('2015-12-28'), 
                                date('2015-12-29'), 
                                date('2015-12-30'), 
                                date('2015-12-31'), 
                                date('2016-01-01'), 
                                date('2016-01-02') ] 
    """

    yyyy = d.year
    nn = list()
    prev = 0

    for ii in range(7):
        dx = (d  - datetime.timedelta(ii))
        doy = dx.timetuple().tm_yday
        if prev  == 1:
            yyyy = yyyy -1
        prev = doy
        nn.append(  dx )

    nn.reverse()
    return nn


#=====================

def usage():
    usage_text = "Usage:\t%s -u <https://company.harvestapp.com> -e <email> -p <password> -d yyyy-mm-dd -c <client_name>\n\t%s -u <https://company.harvestapp.com> -e <email> -p <password>  --date_key yyyy-mm-dd --client_name <client_name>"

    print(usage_text % (sys.argv[0], sys.argv[0]))


def main(argv):


    try:
        opts, args = getopt.getopt(sys.argv[1:], "u:e:p:d:c:", ["url=","email=","password=","date_key=","client_name="])

        if not opts:
            raise getopt.GetoptError('No options supplied')

        if len(opts) != 5:
            print getopt.GetoptError('Incorrect number of options supplied')

    except getopt.GetoptError,e:
        print e
        usage()
        sys.exit(2)
 
    print opts
    for o, a in opts:
        
        if   o in ("-u", "--url"):
            url = a
        elif o in ("-e", "--email"):
            email = a
        elif o in ("-p", "--password"):
            password = a
        elif o in ("-d", "--date_key"):
            date_key = a
        elif o in ("-c", "--client_name"):
            client_name = a

    # get all the dates in this week, but we really need start/end
    end_date= datetime.datetime.strptime(date_key, "%Y-%m-%d").date()
    dates = get_dates_for_week_ending(end_date)
    start_date = dates[0]

    svc = harvest.Harvest(url,email,password)

    gavel = get_client_by_name(svc, client_name)

    gavel_id = gavel['client']['id']

    projects = svc.projects_for_client(gavel_id)


    # Codes/IDs for active projects only
    pa = [(p['project']['code'],p['project']['id']) for p in projects if p['project']['active']==True]


    for project in pa:
       
        print(project, end_date)
        project_code = project[0]
        project_id = project[1]
        ts_entries = svc.timesheets_for_project( project_id, start_date, end_date)
        print len(ts_entries)


        for item in ts_entries:
            #pprint(item)
            user = get_user(svc, item['day_entry']['user_id'])
            project = get_project(svc, item['day_entry']['project_id'])
            the_date = item['day_entry']['spent_at']
            summary = get_summary(the_date, project, user)
            summary.add_entry(item)


    records = sorted(SUMMARIES.values(), key=lambda x: x.key)

    filename = "output/%s-%s-time.txt" % (date_key.replace("-",""), client_name)
    f = open(filename,'w')
    f.write("date\tproject\tuser\ttime\tnotes\tentries\n")
    for s in records:
        f.write(s.to_tsv_record())
    f.close()




if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


