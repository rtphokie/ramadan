'''
Created on May 19, 2018
dates assume 00:00 UTC
@author: trice
'''
import unittest
from hijri_date import HijriDate
from math import radians as rad, degrees as deg  
import ephem  
from datetime import datetime, timedelta
from matplotlib import pyplot as plt, matplotlib_fname
import pandas as pd
import numpy as np

# based on Islamic calendar calculations by Borni DHIFI
# https://github.com/borni-dhifi/ummalqura

pd.options.display.max_rows = 999
pd.options.display.max_columns = 9999

# use Raleigh, NC coordiantes for sunrise/set calcualtions
lat=35.78 
lon=-78.64

def local_sunset(g, h_year, h_month):
    sun = ephem.Sun(g)
    g.date = Hijri2Gregorian(HijriDate(h_year,h_month,1))                # set UTC midnight calculated day
    g.date = g.next_transit(sun)                                         # set time to local solar transit
    sunset = ephem.localtime(g.next_setting(sun)).replace(microsecond=0) # set time to local sunset
    return sunset

def dRamadan_begin_end(lat, lon, date=None):
    if date == None:
        date = datetime.now()

    g = ephem.Observer()
    g.lat=rad(lat)  # lat/long in decimal degrees  
    g.long=rad(lon)  

    um = HijriDate(date.year,date.month,date.day, gr=True)
    if um.month > 9:
        h_year = um.year + 1
    else:
        h_year = um.year
        
    begin = local_sunset(g, h_year, 9)
    end = local_sunset(g, h_year, 10)

    return begin, end

def table():

    g = ephem.Observer()
    g.name='Raleigh'  
    g.lat=rad(35.78)  # lat/long in decimal degrees  
    g.long=rad(-78.64)  
    
    moon = ephem.Moon(g)
    sun = ephem.Sun(g)
    results = []
    for h_year in range (1431,1442):
        print
        um = HijriDate(h_year,9,1)
        Hijri_str = "%02d-%02d-%d" % (um.day, um.month, um.year)
        print Hijri_str
        print "            Gregorian: %d/%d/%d" %(um.year_gr, um.month_gr, um.day_gr)

        g.date = ephem.Date("%d/%d/%d" %(um.year_gr, um.month_gr, um.day_gr, )) # midnight UTC
        g.date = g.next_transit(sun, start=g.next_rising(sun))
        print '        solar transit: %s' % datetime.strftime(ephem.localtime(g.date), '%c')
        sunset1 = g.next_setting(sun)
        print '               sunset: %s' % datetime.strftime(ephem.localtime(sunset1), '%c')
        
        #lunar circumstances at local sunset
        g.date = sunset1
        moon.compute(g)
        print '  lunar alt at sunset: %.1f' %  deg(moon.alt) 
        print 'lunar elong at sunset: %.1f' % deg(moon.elong)
        print 'lunar phase at sunset: %.1f%%' % moon.phase
        
        # https://moonsighting.com/ramadan-eid.html
        # http://www.fiqhcouncil.org/node/83
        if  deg(moon.alt) >= 5.0 and deg(moon.elong) >= 8.0:
            start = sunset1
        else:
            start = g.next_setting(sun)
        results.append(start)

        newmoon2 = ephem.next_new_moon(g.date ) 
        g.date = newmoon2
        end = g.next_setting(sun)
        print '        new moon     : %s UTC' % datetime.strftime(newmoon2.datetime(), '%c')

        print '        Ramadan_begin_end start: %s' % datetime.strftime(ephem.localtime(start), '%c')
        print '        Ramadan_begin_end end  : %s' % datetime.strftime(ephem.localtime(end), '%c')

    return results

def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + timedelta(n)

def Hijri2Gregorian(h_year, h_month, h_day):
    h = HijriDate(h_year, h_month, h_day)
    return datetime(int(h.year_gr), int(h.month_gr), int(h.day_gr))

def RamadanStart(h_year):
    return Hijri2Gregorian(h_year, 9, 1)

def RamadanEnd(h_year):
    return Hijri2Gregorian(h_year, 10, 1)

def localsunset(date, lat, lon):
    return localriseset(date, lat, lon, 'set')

def localsunrise(date, lat, lon):
    return localriseset(date, lat, lon, 'rise')

def localriseset(date, lat, lon, riseset):
    g = ephem.Observer()
    g.lat=rad(lat)  # lat/long in decimal degrees  
    g.long=rad(lon)  
    sun = ephem.Sun(g)
    g.date = date    
                                                        # set UTC midnight calculated day
    if riseset == 'set':
        risesetfunction = g.next_setting
    elif riseset == 'rise':
        risesetfunction = g.previous_rising
    else:
        raise SyntaxError ('expected rise or set')
    g.date = g.next_transit(sun)                                         # set time to local solar transit
    event = ephem.localtime(risesetfunction(sun)).replace(microsecond=0) # set time to local sunset
    return event

def daylight_hours(start, end):
    df_daily = pd.DataFrame({ 'date': pd.date_range(start=start, end=end)})
    df_daily['sunset'] = df_daily['date'].apply((lambda x: localsunset(x, lat, lon)))
    df_daily['sunrise'] = df_daily['date'].apply((lambda x: localsunrise(x, lat, lon)))
    df_daily['daylight'] = df_daily['sunset'] - df_daily['sunrise']
    return pd.Series([df_daily['daylight'].min(), 
                      df_daily['daylight'].mean(),
                      df_daily['daylight'].max()])


class Test(unittest.TestCase):

    def setUp(self):
        self.df = pd.DataFrame({ 'Islamic year' : range(1400,1500)})
        self.df.set_index('Islamic year', inplace=True)
        self.df['start date'] = self.df.index.map(RamadanStart)
        self.df['end date'] = self.df.index.map(RamadanEnd)
        self.df['local start'] = self.df['start date'].apply((lambda x: localsunset(x, lat, lon)))
        self.df['local end'] = self.df['end date'].apply((lambda x: localsunset(x, lat, lon)))
        self.df['Gregorian year'] = self.df['local start'].apply((lambda x: x.year))

    def test_month_length(self):
        df = self.df
        df['length'] = df['local end'] - df['local start']
        df['days'] = df['length'].apply(lambda x: (x + timedelta(days = 0.5)).days)  # rounding by day

        print 'longest Ramadan month'
        print '-' * 30
        print df.ix[df['length'].idxmax()]

        print
        print 'shortest Ramadan month'
        print '-' * 30
        print df.ix[df['length'].idxmin()]

        print 'count of (rounded) days in Ramadan 1400-1500'
        print df['days'].value_counts()

    def test_twice_in_Gregorian_year(self):
        df = self.df
        df['occurrences'] = df.groupby('Gregorian year')['Gregorian year'].transform('count')

        print
        print 'Gregorian years where Ramadan falls twice'
        print '-' * 30
        print df[df['occurrences'] >1 ][['Gregorian year', 'local start', 'local end']]

    def test_daylight_hours(self):
        df = self.df
        # calc daylight hours
        df[['max', 'mean', 'min']]  = df.apply(lambda row: daylight_hours(row['start date'], row['end date']), axis=1)
        df['mean hours'] = df['mean'].apply(lambda row: row.total_seconds()/3600)
        
        # cal Ramadan position in the Gregorian year
        df['gyear'] = df['start date'].dt.year
        df['start'] = df['start date'].dt.dayofyear
        df['end'] = df['end date'].dt.dayofyear
        
        plt.xkcd()  # use XKCD sketch plotting style
        _, ax = plt.subplots()
        axy2 = ax.twiny()
        axx2 = ax.twinx()

        # mean hours of daylight, Y axis right, color = '#b59410 xkcd:gold',
        axx2.plot(df.index, df['mean hours'], lw = 4, alpha = 1, color="#b59410", label='daylight hours')
        axx2.set_ylabel('hours of daylight', color='#b59410', fontsize=20)
        axx2.tick_params('y', colors='#b59410', right=False)

        # graph month starts in Gregorian sized chunks, Y axis left color='#1f77b4, tableau blue', 
        x_data_chunk = []
        y_chunk = []
        for y, x in zip(df['end'], df.index):
            try: 
                prev = y_chunk[-1]
            except:
                prev = y
            if prev < y:
                ax.plot(x_data_chunk, y_chunk, lw=4, alpha=1, color='#1f77b4', label='Ramadan Start')
                x_data_chunk = [x]
                y_chunk = [y]
            else:
                x_data_chunk.append(x)
                y_chunk.append(y)

        # Y axis left
        ax.set_ylim(0,365)
        ax.set_yticks([x*(365/12.0)+15 for x in range(0,12)])
        ax.set_yticklabels(['Jan','','Mar','','May','','Jul','','Sep','','Nov',''], color='#1f77b4')
        ax.set_ylabel('Ramadan start (Gregorian)', color='#1f77b4', fontsize=20, alpha=0.75)
        ax.tick_params('y', colors='#1f77b4', left=False)

        # X axis bottom
        ax.set_xlabel('Year (Islamic)', color='#b', fontsize=12, alpha=0.75)
        ax.xaxis.label.set_color('#7f7f7f')
        ax.tick_params(axis='x', colors='#7f7f7f', labelsize=10, bottom=False)

        # X axis top
        axy2.set_xlim(df['gyear'].min(), df['gyear'].max())
        axy2.set_xlabel("year (Gregorian)", fontsize=12, color='#7f7f7f', alpha=0.75)
        axy2.tick_params(axis='x', color='#7f7f7f', labelsize=10, top=False)

        # remove chart spines for easier reading
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_visible(False)

        plt.savefig('Ramadan_variance.png')
        plt.show()
        

if __name__ == "__main__":
    unittest.main()