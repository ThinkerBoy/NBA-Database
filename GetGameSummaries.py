# -*- coding: utf-8 -*-
"""
Created on Sat Nov 26 12:54:45 2016

@author: DanLo1108
"""


#Import packages

from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import urllib2
import re
import string as st
import sqlalchemy as sa
import os
import yaml


#Function which takes a date string and appends game summaries
#to PostGres database
def append_game_summary(date_str,engine):
    
    #Define URL from ESPN
    url='http://www.espn.com/nba/scoreboard/_/date/'+date_str
    
    #Get URL page 
    request=urllib2.Request(url)
    page = urllib2.urlopen(request)
    
    #Get content from URL page
    content=page.read()
    soup=BeautifulSoup(content,'lxml')
    
    #Get scripts
    scripts=soup.find_all('script')
    
    #Get results from scripts
    results=[script.contents[0] for script in scripts if len(script.contents) > 0 and '{"leagues"' in script.contents[0]][0]
    #results=scripts[9].contents[0]
    results=results[results.index('{"leagues"'):results.index(';window.')]
    results=re.sub('false','False',results)
    results=re.sub('true','True',results)
    
    events=eval(results)['events']
    
    #Iterate through "events" i.e. games
    scoreboard_results=[]
    for event in events:
        game_id=event['id'] #Game ID
        date=date_str[4:6]+'-'+date_str[6:]+'-'+date_str[:4] #Date
        season=event['season']['year'] #Season
        
        #Get venue/attendance
        if 'venue' in event['competitions'][0]:
            venue=event['competitions'][0]['venue']['fullName']
            if 'address' in event['competitions'][0]['venue']:
                if 'state' in event['competitions'][0]['venue']['address'] and 'city' in event['competitions'][0]['venue']['address']:
                    location=event['competitions'][0]['venue']['address']['city']+', '+event['competitions'][0]['venue']['address']['state']
                else:
                    location=None
            else:
                location=None
            venue_id=event['competitions'][0]['venue']['id']
        else:
            venue=None
            location=None
            venue_id=None
        attendance=event['competitions'][0]['attendance']
        
        #Get game type (preseason/reg season/postseason)
        if 'type' in event['season']:
            if event['season']['type']==1:
                game_type='Preseason'
            elif event['season']['type']==2:
                game_type='Regular Season'
            elif event['season']['type']==3:
                game_type='Playoffs'
        else:
            game_type=None
        
        #Get long and short headlines for game
        if 'headlines' in event['competitions'][0]:
            if 'description' in event['competitions'][0]['headlines'][0]:
                headline_long=re.sub('&#39;',"'",event['competitions'][0]['headlines'][0]['description'])
            else:
                headline_long=None
            if 'shortLinkText' in event['competitions'][0]['headlines'][0]:
                headline_short=re.sub('&#39;',"'",event['competitions'][0]['headlines'][0]['shortLinkText'])
            else:
                headline_short=None
        else:
            headline_long=None
            headline_short=None
            
        #Get home team details (name, abbreviation, ID, score, WinFLG)
        home_team=event['competitions'][0]['competitors'][0]['team']['displayName']
        if 'abbreviation' in event['competitions'][0]['competitors'][0]['team']:
            home_team_abbr=event['competitions'][0]['competitors'][0]['team']['abbreviation']
        else:
            home_team_abbr=None
        home_team_id=event['competitions'][0]['competitors'][0]['team']['id']
        home_team_score=event['competitions'][0]['competitors'][0]['score']
        if 'winner' in event['competitions'][0]['competitors'][0]:
            home_team_winner=event['competitions'][0]['competitors'][0]['winner']
        else:
            home_team_winner=None
            
        #Get away team details (name, abbreviation, ID, score, WinFLG)    
        away_team=event['competitions'][0]['competitors'][1]['team']['displayName']
        if 'abbreviation' in event['competitions'][0]['competitors'][1]['team']:
            away_team_abbr=event['competitions'][0]['competitors'][1]['team']['abbreviation']
        else:
            away_team_abbr=None
        away_team_id=event['competitions'][0]['competitors'][1]['team']['id']
        away_team_score=event['competitions'][0]['competitors'][1]['score']
        if 'winner' in event['competitions'][0]['competitors'][1]:
            away_team_winner=event['competitions'][0]['competitors'][1]['winner']
        else:
            away_team_winner=None
            
        #Get series summary, if postseason game
        if 'series' in event['competitions'][0]:
            series_summary=event['competitions'][0]['series']['summary']
        else:
            series_summary=None
            
        #Get team records
        if 'records' in event['competitions'][0]['competitors'][0]:
            home_team_overall_record=event['competitions'][0]['competitors'][0]['records'][0]['summary']
            home_team_home_record=event['competitions'][0]['competitors'][0]['records'][1]['summary']
            home_team_away_record=event['competitions'][0]['competitors'][0]['records'][2]['summary']
        else:
            home_team_overall_record=None
            home_team_home_record=None
            home_team_away_record=None
            
        if 'records' in event['competitions'][0]['competitors'][1]:
            away_team_overall_record=event['competitions'][0]['competitors'][1]['records'][0]['summary']
            away_team_home_record=event['competitions'][0]['competitors'][1]['records'][1]['summary']
            away_team_away_record=event['competitions'][0]['competitors'][1]['records'][2]['summary']
        else:
            away_team_overall_record=None
            away_team_home_record=None
            away_team_away_record=None
            
        #Get game statuses - Completion and OT
        if 'status' in event:
            status=event['status']['type']['description']
            try:
                ot_status=event['status']['type']['altDetail']
            except:
                ot_status='Reg'
        else:
            status=None
            ot_status=None
            
        
        #Append game results to list   
        scoreboard_results.append((game_id,status,ot_status,date,season,home_team,away_team,home_team_score,
                                  away_team_score,location,venue,venue_id,attendance,
                                  game_type,headline_long,headline_short,
                                  home_team_abbr,home_team_id,
                                  home_team_winner,away_team_abbr,
                                  away_team_id,away_team_winner,series_summary,
                                  home_team_overall_record,home_team_home_record,home_team_away_record,
                                  away_team_overall_record,away_team_home_record,away_team_away_record))
    
    #Define column names
    col_names=['GameID','Status','StatusDetail','Date','Season','HomeTeam','AwayTeam','HomeTeamScore','AwayTeamScore',
              'Location','Venue','VenueID','Attendance','GameType',
             'HeadlineLong','HeadlineShort','HomeTeamAbbr','HomeTeamID',
             'HomeTeamWinner','AwayTeamAbbr','AwayTeamID',
             'AwayTeamWinner','PlayoffSeriesSummary',
             'HomeTeamOverallRecord','HomeTeamHomeRecord','HomeTeamAwayRecord',
             'AwayTeamOverallRecord','AwayTeamHomeRecord','AwayTeamAwayRecord']  
     
    #Save all games for date to DF                           
    scoreboard_results_df=pd.DataFrame(scoreboard_results,columns=col_names)
    
    #Append dataframe results to MySQL database
    scoreboard_results_df.to_sql('game_summaries',con=engine,schema='nba',index=False,if_exists='append')
    
    


#Get credentials stored in sql.yaml file (saved in root directory)
if os.path.isfile('/sql.yaml'):
    with open("/sql.yaml", 'r') as stream:
        data_loaded = yaml.load(stream)
        
        #domain=data_loaded['SQL_DEV']['domain']
        user=data_loaded['BBALL_STATS']['user']
        password=data_loaded['BBALL_STATS']['password']
        endpoint=data_loaded['BBALL_STATS']['endpoint']
        port=data_loaded['BBALL_STATS']['port']
        database=data_loaded['BBALL_STATS']['database']


#Create PostgreSQL engine with SQL Alchemy with credentials. 
db_string = "postgres://{0}:{1}@{2}:{3}/{4}".format(user,password,endpoint,port,database)
engine=sa.create_engine(db_string)


#Get max dates of games that were scheduled but not completed
#**This does not work for postseason
max_date_query='''

select 
    max(cast("Date" as date)) max_date
from 
    nba.game_summaries
where
    "Status"='Final'
    
'''

#Iterate through date strings to get game summaries for each date
from datetime import datetime
from datetime import date
start = pd.read_sql(max_date_query,engine).loc[0]['max_date']
end = date.today()

dates=[str(d)[:4]+str(d)[5:7]+str(d)[8:10] for d in pd.date_range(start, end) if d.month < 7 or d.month >= 10]


#Iterate through list of dates, appending each days games
cnt=0
bad_dates=[]
for date_str in dates: 
    try:
        append_game_summary(date_str,engine)
        cnt+=1
        if np.mod(cnt,100) == 0:
            print str(round(float(cnt*100.0/len(dates)),2))+'%' 
    except:
        bad_dates.append(date_str)
        cnt+=1
        if np.mod(cnt,100) == 0:
            print str(round(float(cnt*100.0/len(dates)),2))+'%' 
        continue
    
 

#Drop old rows from games that were scheduled and now completed
drop_old_rows_query='''

delete from
    nba.game_summaries gs
where
    "Status" != 'Final'
    and cast("Date" as Date) < (now() - interval '1 day')
    
'''

engine.execute(drop_old_rows_query)

    
    
    
#Drop duplicate rows
#unique_df=pd.read_sql('select distinct * from nba.game_summaries',engine)
#unique_df.to_sql('game_summaries',con=engine,schema='nba',index=False,if_exists='replace')















