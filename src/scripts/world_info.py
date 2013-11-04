# -*- coding: utf-8 -*- 

import urllib2
import re
from google.appengine.ext import db
import datetime
import logging
import app_enviroment
from filters import timezone

class Area(db.Model):
	area_num = db.IntegerProperty()
	base_num = db.IntegerProperty()
	durability = db.IntegerProperty()
	backbone = db.IntegerProperty()
	date = db.DateTimeProperty(auto_now_add=True)

class AreaInformation:
	area_num = 0	

	def __init__(self, area_num):
		self.area_num = area_num
	
	# 保存されているエリア耐久値の時間ごとの差分を平均をします
	def averageDurabilityDiff(self,areas):
	        count = 0
	        s = 0
	
	        for a1,a2 in zip( areas[1:],areas[:-1] ):
	        
	                if a1.base_num != a2.base_num:
	                        continue
	
	                s += a2.durability - a1.durability
	                count +=1
	
		if count == 0:
			return 0
	        result = float(s)/count
	
	        return result
	
	# エリアの１分毎のダメージ平均を求めます
	# hours:何時間前から平均を求める指定します
	# 
	def averageDamage(self,hours):
		lifetime = datetime.timedelta(hours=hours)
		threshold = datetime.datetime.now() - lifetime
		
		# 同じエリアで、指定時間内の情報を日付順でソートして取得
		query = "WHERE area_num =:1 AND date > :2 ORDER BY date"
	
		#同じエリアだけを取得
		areas = Area.gql(query,self.area_num,threshold).fetch(100)
		diffAverage = self.averageDurabilityDiff(areas)
		return diffAverage / app_enviroment.scraping_gap

class WorldInformation:
	def averageDamage(self, hours):
	
		s=0
		count = 0
		for num in range(1,8):
			#指定エリアの平均ダメージを取得
			areaInfo = AreaInformation(num)
			d = areaInfo.averageDamage(hours)
			#潰れたエリアor変化の無いエリアは対象外	
			if d != 0:
				s += d
				count += 1
		if count == 0:
			return 0
		#　エリアのダメージ平均
		return s / count

	def totalDurability(self):
		areas = Area.all().order("-date")
		# 最新のエリアのみを取得
		current_areas = areas.filter("date =" , areas.get().date)

		s = 0
		for area in current_areas:
			if area.base_num == 0:
				continue
			s += (area.base_num - 1)*400000 + area.durability

		return s

	def predictLatestRemainingMinutes(self, hours):
		damage = self.averageDamage(hours)
		if damage == 0:
			return 0
		# あと何分で戦争が終わるか求める
		minutes = self.totalDurability() / damage
		return minutes

	def predictLatestTime(self, hours):
		remaining_minutes = self.predictLatestRemainingMinutes(hours)
		remtime = datetime.timedelta(minutes=remaining_minutes)
		remdate = datetime.datetime.now() + remtime
		return remdate.replace(tzinfo=timezone.UtcTzinfo())

def getCurrentArea():
	url = 'http://acvdlink.armoredcore.net/p/acop/acvdlink/'
	op = urllib2.urlopen(url)
	html = op.read()
	op.close()

	#areainfoを取得する
	areas_regstr = "valArr\[\"areainfo\"\] = \[((?:.|\\n)+?)\];"
	match = re.search(areas_regstr, html)	

	areainfo = match.group(1)

	#各エリアに分割
	area_strs = re.findall("\[((?:.|\n)+?)\]",areainfo)
	
	date = datetime.datetime.now()
	areas = []
	#最初の要素はコメントなので無視
	for area in area_strs[1:]:
		data = area.split(',')
		
		arnum = re.search("([0-9])+",data[0]).group(1)
		
		a = Area()
		a.area_num = int(arnum)
		a.base_num = int(data[5])
		a.durability = int(data[9])
		a.backbone = int(data[12])
		a.date = date
		areas.append( a )

	return areas


