import requests
import webbrowser
import ctypes
import os
import getpass
import urllib, urllib2, cookielib
import shutil
from requests import session
from bs4 import BeautifulSoup

site = "http://www.furaffinity.net/"

#Important: Variables defined in a function that will be reused outside of it must be defined globally using "global variableToBeDefined" without quotes.

headerData = {  'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36',
                'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language':'en-US,en;q=0.8',
                'Accept-Charset':'ISO-8859-1,utf-8;q=0.7,*;q=0.7'
              }

loggedIn = 0
username = None

def getCaptcha():
  global captcha

  url = 'https://www.furaffinity.net/captcha.jpg'
  captcha = c.get(url, stream=True, headers=headerData)
  with open('captcha.jpg', 'wb') as out_file:
    shutil.copyfileobj(captcha.raw, out_file)
  os.system('start captcha.jpg')
  captcha = raw_input("Captcha (captcha.jpg): ")

def login():
  global username

  #AUTOLOGIN MODE REDACTED FOR RELEASE. NEED TO FIND A SECURE METHOD OF STORING USERNAME AND PASSWORD IN EXTERNAL FILE (MAYBE) FOR EASE OF SCRIPT SHARING THAT DOESN'T INVOLVE HARDCODED CREDENTIALS. THAT'S BAD PRACTICE, M'KAY?
  print "Manual login mode\n"
  while True:
    username = raw_input("Username: ")
    if username != "":
      password = getpass.getpass()
      break
    else:
      print "You must type a username!"

  getCaptcha()
  print "Logging in as " + str(username) + "..."

  payload = {
      'action': 'login',
      'name': username,
      'pass': password,
      'use_old_captcha': '1',
      'captcha': captcha
  }

  c.post('https://www.furaffinity.net/login', data=payload, headers=headerData)
  responseLogin = c.get('http://www.furaffinity.net/msg/pms/', headers=headerData)

  systemMessage = False

  for line in responseLogin.text.splitlines():
    #Scan for a system message. There is a problem with the login if this appears.
    if "System Message" in line:
      print "\nInvalid username, password, or captcha"
      systemMessage = True
      username = None
      break
  if systemMessage == False:
    global loggedIn
    loggedIn = 1
    print "\nLogged in!"

def logout():
  print "\nLogging out..."
  c.get('http://www.furaffinity.net/logout-link', headers=headerData)

  global loggedIn
  global username
  loggedIn = 0
  username = None

def showLoginName():
  if username != None:
    print "Logged in as " + username + "\n"

def statusCheck():
  global status

  r = requests.head(site, headers=headerData)
  status = str(r.status_code)
  #status = str(500)
  #fake site status

def statusHandler():
  if status != "200":
    halt("The site was unreachable because", status)
    return 1

def loginCheck():
  if loggedIn != 1:
    halt(None, "NEED_LOGIN_TO_VIEW")
    return 1

def statusPrinter():
  global status

  status_map = {  "200" : "200 - OK",
                  "301" : "301 - Moved Permanently",
                  "404" : "404 - Not Found",
                  "500" : "500 - Internal Server Error",
                  "501" : "501 - Not Implemented",
                  "503" : "503 - Service Unavailable",
                  "504" : "504 - Gateway Timeout",
                  "524" : "524 - A Timeout Occurred (CloudFlare)",
                  "598" : "598 - Network Read Timeout"
                }
  
  if status in status_map:
    status = status_map[status]
  else:
    status = status + " - (Unknown Status Code)"
  print "\nThe site status code is " + status

def responseWriter():
  print "\nConnecting to " + site + "..."
  siteResponse = c.get(site, headers=headerData)

  f1 = open('FA_HTMLHeader.fap', 'w+')
  print "\nWriting site headers to " + str(f1) + "..."
  f1.write(str(siteResponse.headers))
  print "Done!"
  f1.close()

  f2 = open('FA_HTMLContent.fap', 'w+')
  print "\nWriting site HTML to " + str(f2) + "..."
  f2.write(str(siteResponse.text))
  print "Done!"
  f2.close()

  f3 = open('FA_Status.fap', 'w+')
  print "\nWriting site status code to " + str(f3) + "..."
  statusCheck()
  f3.write(status)
  f3.flush()
  f3.seek(0)
  print "Done!"
  statusPrinter()
  f3.close()

def updateSubmissionsOnline():
  responseSubmissions = c.get('http://www.furaffinity.net/msg/submissions/', headers=headerData)
  #responseNotes = c.get('http://www.furaffinity.net/msg/pms/', headers=headerData)
  #Change responseSubmissions variable at your leisure, this is just an example
  #print(responseSubmissions.headers)
  #print(responseSubmissions.text)
  global contentSubmissions
  contentSubmissions = responseSubmissions.text

def updateSubmissionsLocalFile():
  #Local HTML fap files
  #fileNotes = open('notes.fap', 'r')
  #global contentNotes
  #contentNotes = fileNotes.read()

  fileSubmissions = open('submissions.fap', 'r')
  global contentSubmissions
  contentSubmissions = fileSubmissions.read()

def parseSubmissions():
  global numberOfSubmissions
  global submissionList
  global maxTitleWidth
  global maxArtistWidth
  global maxRatingWidth
  global adminNotice
  global adminMessage
  numberOfSubmissions = 0
  submissionList = []
  maxTitleWidth = 0
  maxArtistWidth = 0
  maxRatingWidth = 0
  adminNotice = None
  adminMessage = None

  for line in contentSubmissions.splitlines():
    #All submissions have sid_ in them
    if "sid_" in line:
      #Looks at each submission one at a time
      line.split('\n')
      #Reads and parses HTML in BeautifulSoup
      soup = BeautifulSoup(line, "html.parser")
      #Convert ratings to a human readable format. Ratings are found in the b tag's class. There are 2 classes in it. Extract the first class for rating info [0]
      rating = soup.find("b")['class'][0]

      rating_map = {  "r-general" : "General",
                      "r-mature" : "Mature",
                      "r-adult" : "Adult"
                    }
      
      if rating in rating_map:
        rating = rating_map[rating]
      else:
        rating = "Unknown"

      #Finds the text of the title (HTML tags are nested in the current line, ending with the raw text of the span)
      submissionTitle = soup.b.span.text
      #We need to skip the first small tag since there are 2 of them in our line. We will put [1] to do this. Artist name is in the anchor link text
      submissionArtist = soup.findAll('small')[1].a.text
      numberOfSubmissions += 1
      #Finds the max length of the titles, artists, and ratings for later use in our dynamically expanding table.
      if maxTitleWidth < len(submissionTitle):
        maxTitleWidth = len(submissionTitle)
      if maxArtistWidth < len(submissionArtist):
        maxArtistWidth = len(submissionArtist)
      if maxRatingWidth < len(rating):
        maxRatingWidth = len(rating)

      submissionList.append((submissionTitle, submissionArtist, rating))
      #TODO: check for music uploads, t-image is the most frequently used but there could be writing and songs parsed later on. Don't forget this!

    if "admin_notice_do_not_adblock" in line:
      line.split('\n')
      adminNotice = BeautifulSoup(line, "html.parser")
      try:
        adminNotice = adminNotice.h2.text
        #adminNoticeHeader = ["Administrator Notice".center(len(adminNotice))]
        adminNoticeTable = u'\u2502 {0:{a}} \u2502'

        def newRowNotice():
          print u'\u2500' * (len(adminNotice) + 4)

        print ""
        #newRowNotice()
        #print adminNoticeTable.format(*adminNoticeHeader,a=len(adminNotice))
        newRowNotice()
        print adminNoticeTable.format(*[adminNotice],a=len(adminNotice))
        newRowNotice()
      except AttributeError:
        adminNotice = None

  try:
    adminMessage = BeautifulSoup(contentSubmissions, "html.parser")
    adminMessage = adminMessage.h4.parent.text
    print adminMessage
  except AttributeError:
    adminMessage = None

def printSubmissions():
  if numberOfSubmissions == 0:
    print "There are no submissions to list"
  else:
    header = ("Title", "Artist", "Rating")
    def newRow():
      "Creates a row as wide as the submissions table. The number at the end adds more width for the spaces and borders"
      print u'\u2500' * (maxTitleWidth + maxArtistWidth + maxRatingWidth + 10)
    newRow()
    #Instead of hardcoded width values, let's make them dynamic, based on the longest text string for each column!
    columnWidths = u'\u2502 {0:{t}} \u2502 {1:{a}} \u2502 {2:{r}} \u2502'
    print columnWidths.format(*header,t=maxTitleWidth,a=maxArtistWidth,r=maxRatingWidth)
    newRow()
    for submission in submissionList:
      print columnWidths.format(*submission,t=maxTitleWidth,a=maxArtistWidth,r=maxRatingWidth)
    newRow()
    print "\nThere",
    if numberOfSubmissions == 1:
      print "is 1 submission",
    else:
      print "are " + str(numberOfSubmissions) + " submissions",
    print "total"

def displaySubmissions():
  parseSubmissions()
  print "\nCurrent Furaffinity Submissions:\n"
  printSubmissions()

def showAdminMessages():
  parseSubmissions()
  if adminNotice == None:
    print "\nNo special modes active"
  if adminMessage == None:
    print "\nNo administrator message"

def clear():
  os.system('cls' if os.name == 'nt' else 'clear')

def halt(reasonInput = None, errorCode = "None"):
  reason = reasonInput

  def giveReason():
    if reasonInput != None:
      print "\nReason: " + reason, #comma will allow modular message sections to appear on the same line (like with error code descriptions)
    else:
      pass

  #halt() error integers are to be exclusively used for HTTP status codes only
  if errorCode.isdigit():
    print "\nThis option can't be used right now"
    giveReason()
    if errorCode == "301":
      print "the site is being redirected to an invalid page"
    elif errorCode == "404":
      print "the page does not exist (OMG FURAFFINITY GOT DELETED?!)"
    elif errorCode in {"500", "501", "503", "504", "524", "598"}:
      print "the server is having problems"
    else:
      print "FA is malfunctioning"
    statusPrinter()
    pause()
    return
  elif errorCode == "NEED_LOGIN_TO_VIEW":
    print "\nYou will need to login before using this option"
    pause()
  elif errorCode == "ALREADY_LOGGED_IN":
    print "\nYou are already logged in as " + username
    pause()
  else:
    print "\nAn error has occured. This program cannot continue."
    giveReason()
    print ""
    quitPrompt()
    logout()
    quit()
  
def quitPrompt():
  raw_input("\nPress enter to quit...")

def pause():
  raw_input("\nPress enter to continue...")

def quit():
  raise SystemExit(0)

clear()
with session() as c:
  while True:
    showLoginName()
    updateMode = raw_input("Please make a selection:\n\n1: Login to " + site + "\n2: Show current submissions online\n3: Load submissions from file (submissions.fap)\n4: Write current FA site response headers, statuses, and more to files\n5: Check current site status code\n6: Check for admin notice online (login)\n7: Check for admin notice offline (submissions.fap)\nl: Logout\nq: Quit\n")
    if updateMode != "":
      if updateMode == "1":
        statusCheck()
        errorFound = statusHandler()
        if errorFound != 1:
          if loggedIn == 1:
            halt(None, "ALREADY_LOGGED_IN")
          else:
            login()
            pause()
            clear()
        clear()
      elif updateMode == "2":
        statusCheck()
        errorFound = statusHandler()
        errorFound = loginCheck()
        if errorFound != 1:
          updateSubmissionsOnline()
          displaySubmissions()
          pause()
          clear()
        clear()
      elif updateMode == "3":
        updateSubmissionsLocalFile()
        displaySubmissions()
        pause()
        clear()
      elif updateMode == "4":
        responseWriter()
        pause()
        clear()
      elif updateMode == "5":
        print "\nChecking..."
        statusCheck()
        statusPrinter()
        pause()
        clear()
      elif updateMode == "6":
        statusCheck()
        errorFound = statusHandler()
        errorFound = loginCheck()
        if errorFound != 1:
          updateSubmissionsOnline()
          showAdminMessages()
          pause()
          clear()
        clear()
      elif updateMode == "7":
        updateSubmissionsLocalFile()
        showAdminMessages()
        pause()
        clear()
      elif updateMode == "l":
        logout()
        clear()
      elif updateMode == "q":
        logout()
        quit()
      else:
        clear()
        print "Invalid selection\n"
    else:
      clear()
      print "You must make a selection!\n"
  logout()
print "\nA fatal error has occured: End of program reached."
quitPrompt()
#https://www.furaffinity.net/login/?ref=http://www.furaffinity.net/
#just leaving this here as an idea, try to categorize popular upload themes like YCH, Auctions, Streams, etc.
