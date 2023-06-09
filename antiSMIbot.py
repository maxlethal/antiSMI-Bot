from push_news import *
from config_db import asmi


def user_digest(username: int, parse_date: str = str(datetime.now().date()), part_number: int = 0):
	"""
	Направляет пользователю подборку новостей (дайджест) согласно его запроса и настроек
	Дата и временной интервал последнего запрошенного пользователем дайджеста фиксируются в отдельной таблице базы
	"""
	input_date = datetime.strptime(parse_date, '%Y-%m-%d').date()
	greeting = {
		1: 'утренняя',
		2: 'дневная',
		3: 'вечерняя',
		4: 'ночная'
	}

	if input_date > datetime.now().date() or input_date < datetime.strptime('2022-06-28', '%Y-%m-%d').date():
		bot.send_message(username,
		                 f'🤖📗 Вы ввели дату из далёкого будущего или глубокого прошлого, а тут я бессилен')
	else:
		user_categories, news_amount, is_subscribed, is_header = get_user_settings(username)
		date_df = show_date(parse_date, part_number)
		first_name = pd.read_sql(f"SELECT first_name FROM users WHERE username = '{username}'", asmi).first_name[0]

		if part_number != 0:
			my_news = f'🤖: {first_name}, привет!\n\nТвоя {greeting[part_number]} подборка на\n' \
			          f'{datetime.strptime(parse_date, "%Y-%m-%d").strftime("%d %B %Y")}: 👇\n'
		else:
			my_news = f'🤖: {first_name}, привет!\n\nТвоя подборка за\n' \
			          f'{datetime.strptime(parse_date, "%Y-%m-%d").strftime("%d %B %Y")}: 👇\n'

		if is_subscribed is True:
			user_news_dict = pick_usernews_dict(date_df, username)
		else:
			user_news_dict = pick_usernews_dict(date_df)
		for i, category in enumerate(user_categories):
			russian_title = \
				pd.read_sql(f"SELECT russian_title FROM categories WHERE category = '{category}'",
				            asmi).russian_title[0]
			emoj = pd.read_sql(f"SELECT emoj FROM categories WHERE category = '{category}'", asmi).emoj[0]
			category_news = show_title_4category(user_news_dict, category)
			if category_news:
				category_title = f'\n{emoj} {i + 1}. {russian_title.capitalize()}:\n'
				my_news += category_title
				for labels, news in category_news.items():
					my_news += f'{labels}. {news}\n'

		bot.send_message(username, my_news)
		# Пишем дату последнего дайджеста в специальную таблицу в базе
		digestinfo = {'username': username, 'digest_date': parse_date, 'part_number': part_number}
		digestinfo_df = pd.DataFrame(digestinfo, index=[0])
		user_settings = pd.read_sql(
			f"SELECT * FROM user_digest WHERE username = '{username}'",
			asmi)
		if user_settings.empty:
			digestinfo_df.to_sql(name='user_digest', con=asmi, if_exists='append', index=False)
		else:
			asmi.execute(
				f"UPDATE user_digest SET part_number='{part_number}', digest_date='{parse_date}' WHERE username = '{username}'")


# bot.send_message(username,
#                  f'📌 По заголовку можно прочесть новость подробно: \n'
#                  f'отправь координаты через пробел\n'
#                  f'("5 7" направит 7-ую новость 5-ой рубрики)')


def get_full_news(username: int, message: str):
	"""По запрошенной пользователем координате новости выдаёт полную новость и ссылки на неё"""
	digest_date = pd.read_sql(f"SELECT digest_date FROM user_digest WHERE username = '{username}'", asmi).digest_date[
		0]
	digest_part = pd.read_sql(f"SELECT part_number FROM user_digest WHERE username = '{username}'", asmi).part_number[
		0]
	markdown = """*bold text*"""
	try:
		user_categories, news_amount, is_subscribed, is_header = get_user_settings(username)
		category_number, label = map(int, message.split(' '))
		category = user_categories[category_number - 1]
		date_df = show_date(str(digest_date), digest_part)
		if is_subscribed is True:
			user_news_dict = pick_usernews_dict(date_df, username)
		else:
			user_news_dict = pick_usernews_dict(date_df)
		news_title = user_news_dict[category][['title']].loc[label].title
		full_news = show_full_news(user_news_dict, category, label)
		full_digest = f'🤖 {full_news[0]} 🤖\n\n*{news_title}*\n\n{full_news[1].replace(news_title + ". ", "")}' \
		              f'\n\n👇 СМИ и первоисточники 👇'

		bot.send_message(username, full_digest, parse_mode="Markdown")
		full_news[2].discard('https://t.me/economika')
		for link in full_news[2]:
			bot.send_message(username, link)

	except Exception:
		bot.send_message(username, f'⚠ Неправильно введена координата новости.\n'
		                           f'📗 Нужно ввести еще раз, или почитать инструкцию к боту (команда "help")')


def redefine_user_settings(username: int, categories_letter: str, news_amount: int) -> pd.DataFrame:
	"""
	Переопределяет настройки пользователя в части категорий получаемых им новостей и их количества
	Новые пользовательские настройки записываются в отдельную базу или актуализируются
	"""
	subscribed_users = pd.read_sql(f"SELECT username FROM user_settings WHERE is_subscribed is True", asmi)
	subscribed_users = subscribed_users.username.to_list()

	if username in subscribed_users:
		category_df = pd.read_sql(f"SELECT category, russian_title FROM categories", con=asmi)
		new_category = [category_df.category[category_df.russian_title.str.startswith(el.lower())].iloc[0] for el in
		                categories_letter]

		user_settings = pd.read_sql(f"SELECT * FROM user_settings WHERE username = '{username}'", asmi)
		# Переводим все категорию в False, а затем присваиваем True только тем из них, который указал пользователь
		user_settings[['technology', 'science', 'economy', 'entertainment', 'sports', 'society']] = 'False'
		for category in new_category:
			user_settings[category].iloc[0] = True
		user_settings['news_amount'].iloc[0] = news_amount

		is_subscribed = user_settings.is_subscribed.iloc[0]
		news_amount = user_settings.news_amount.iloc[0]
		show_header = user_settings.show_header.iloc[0]
		technology = user_settings.technology.iloc[0]
		science = user_settings.science.iloc[0]
		economy = user_settings.economy.iloc[0]
		entertainment = user_settings.entertainment.iloc[0]
		sports = user_settings.sports.iloc[0]
		society = user_settings.society.iloc[0]
		asmi.execute(
			f"UPDATE "
			f"user_settings "
			f"SET "
			f"is_subscribed='{is_subscribed}', "
			f"news_amount='{news_amount}',"
			f"show_header='{show_header}',"
			f"technology='{technology}', "
			f"science='{science}', "
			f"economy='{economy}', "
			f"entertainment='{entertainment}', "
			f"sports='{sports}', "
			f"society='{society}' "
			f"WHERE "
			f"username = '{username}'")
		# user_settings.to_sql(name='user_settings', con=asmi, if_exists='append', index=False)
		return user_settings


@bot.message_handler(commands=['start'])
def handle_start(message):
	username = message.chat.id
	bot.send_message(username, start_text)


@bot.message_handler(commands=['help'])
def handle_help(message):
	"""Выводит сообщение с инструкцией к боту"""
	username = message.chat.id
	bot.send_message(username, help_text)


@bot.message_handler(commands=['subscribe'])
def handle_subscribe(message):
	"""Собирает сведения о пользователе и пишет в базу данных"""

	username = message.chat.id
	nickname = message.from_user.username
	first_name = message.from_user.first_name
	last_name = message.from_user.last_name
	subscribe_date = str(datetime.now().date())
	success_subscribed_text = (f"Успешно подписался, {nickname}, спасибо! ❤\n\n"
	                           "Теперь 4 раза в день тебе будет ждать свежая порция новостей.\n\n"
	                           "По умолчанию приходит стандартная сводка: \n"
	                           "- все типы новостей (кроме политики); \n"
	                           "- по три новости в каждой категории.\n\n"
	                           "Изменить параметры можно в настройках.\n\n"
	                           "Хорошего дня!")

	user_dict = {'username': username, 'nickname': nickname, 'first_name': first_name, 'last_name': last_name,
	             'subscribe_date': subscribe_date}
	user_df = pd.DataFrame(user_dict, index=[0])
	all_users = pd.read_sql(f"SELECT username FROM user_settings", asmi)
	all_users = all_users.username.to_list()
	subscribed_users = pd.read_sql(f"SELECT username FROM user_settings WHERE is_subscribed is True", asmi)
	subscribed_users = subscribed_users.username.to_list()
	# если пользователя подписывается впервые
	if username not in all_users:
		# Завели пользователя в users
		user_df.to_sql(name='users', con=asmi, if_exists='append', index=False)
		# Завели настройки для этого пользователя == дефолтным
		default_settings = pd.read_sql(f"SELECT * FROM user_settings WHERE username = 999999999", asmi)
		user_settings = default_settings
		user_settings.username = username
		user_settings.is_subscribed = True
		user_settings.to_sql(name='user_settings', con=asmi, if_exists='append', index=False)
		bot.send_message(username, success_subscribed_text)
	# если пользователь подписывался раннее, но отписался
	elif username not in subscribed_users:
		user_settings = pd.read_sql(f"SELECT * FROM user_settings WHERE username = '{username}'", asmi)
		user_settings.is_subscribed = True
		user_settings.to_sql(name='user_settings', con=asmi, if_exists='append', index=False)
		asmi.execute(f"UPDATE user_settings SET is_subscribed = True WHERE username = '{username}'")

		bot.send_message(username, success_subscribed_text)

	# если пользователь зачем-то захотел подписаться повторно
	else:
		# bot.send_message(username, f"Вы уже подписаны.")
		pass


@bot.message_handler(commands=['unsubscribe'])
def handle_unsubscribe(message):
	"""Отписка от рассылки путем снятия пользовательского флага об участии в рассылке"""
	username = message.chat.id
	nickname = message.from_user.username
	subscribed_users = pd.read_sql(f"SELECT username FROM user_settings WHERE is_subscribed is True", asmi)
	subscribed_users = subscribed_users.username.to_list()
	if username in subscribed_users:
		# user_settings = pd.read_sql(f"SELECT * FROM user_settings WHERE username = '{username}'", asmi)
		# user_settings.is_subscribed = 'False'
		# user_settings.to_sql(name='user_settings', con=asmi, if_exists='append', index=False)
		asmi.execute(f"UPDATE user_settings SET is_subscribed = False WHERE username = '{username}'")

		bot.send_message(username, f"Спасибо что был с нами, {nickname}! Удачи!")


@bot.message_handler(commands=['news'])
def handle_news(message):
	"""Отдаёт пользовательскую подборку"""
	username = message.chat.id  # temp_dict автора сообщения
	user_date = str(datetime.now().date())
	user_digest(username, parse_date=user_date, part_number=0)


@bot.message_handler(content_types=['location'])
def handle_loc(message):
	username = message.chat.id
	coord = (message.location.latitude, message.location.longitude)
	timestamp = str(datetime.now())
	user_coord_dict = {'username': username, 'coord': str(coord), 'timestamp': timestamp}
	df = pd.DataFrame(user_coord_dict, index=[0])
	df.to_sql(name='users_coord', con=asmi, if_exists='append', index=False)

	handle_subscribe(message)
	user_digest(username)


@bot.message_handler(commands=['settings'])
def handle_settings(message):
	"""Даёт подписанным пользователям инструкцию по изменению настроек по умолчанию"""
	username = message.chat.id
	nickname = message.from_user.username

	subscribed_users = pd.read_sql(f"SELECT username FROM user_settings WHERE is_subscribed is True", asmi)
	subscribed_users = subscribed_users.username.to_list()

	if username in subscribed_users:
		settings_text = (f"Стандартная настройка позволяет получать 3 новости без политики.\n"
		                 f"А здесь рассказано, как изменить категории и количество новостей в каждой категории.\n"
		                 f"📗 Настройка пока сложная, прочти внимательно {nickname}!\n\n"
		                 f"🤖 Я умею собирать шесть категорий новостей, каждая из которых начинается со своей буквы:\n"
		                 f"Н - Наука\n"
		                 f"П - Политика и общество\n"
		                 f"Р - Развлечения\n"
		                 f"С - Спорт\n"
		                 f"Т - Технологии и IT\n"
		                 f"Э - Экономика\n\n"
		                 f""
		                 f'Чтобы это изменить, нужно направить мне новые настройки в формате "буквы_слитно" "число"\n'
		                 f'Например, "СТЭ 5" позволит получать по пять новостей спорта, технологий и экономики\n'
		                 f'Остальные категории будут игнорироваться, пока не изменишь настройки ещё раз\n\n'
		                 f'P.S. Название букв можно вводить в любом регистре и последовательности, но только слитно.\n'
		                 f' Нельзя послать только буквы или только число')
		bot.send_message(username, settings_text)
	else:
		bot.send_message(username, 'Чтобы получить доступ с настройкам, нужно подписаться')


@bot.message_handler(content_types=['text'])
def guess_user_request(message):
	"""Пытается угадать желания пользователя по полученному от него сообщению"""
	username = message.chat.id
	answer = message.text
	try:
		valid_date = datetime.strptime(answer, '%Y-%m-%d')
		user_digest(username, parse_date=answer)
	except ValueError:
		try:
			if answer[0].isdigit():
				category_number, label = map(int, answer.split(' '))
				get_full_news(username, answer)
			elif answer[0].isalpha():
				categories_letter = answer.split(' ')[0]
				news_amount = int(answer.split(' ')[1])
				new_user_settings = redefine_user_settings(username, categories_letter, news_amount)
				if type(new_user_settings) == pd.DataFrame and not new_user_settings.empty:
					bot.send_message(username, 'Новые настройки применены')
				else:
					bot.send_message(username, 'Что-то пошло не так')

		except ValueError:
			bot.send_message(username,
			                 '⚠ Могу обрабатывать только дату (формат ГГГГ-ММ-ДД) или координаты новости (два '
			                 'числа через пробел).\n'
			                 '📗 Нужно ввести еще раз, или почитать инструкцию к боту (команда "help")')


def sending_news(part_number):
	"""Делает периодическую рассылку новостей подписавшимся пользователям согласно их настройкам"""
	subscribed_users_df = pd.read_sql(f"SELECT username FROM user_settings WHERE is_subscribed is True", con=asmi)
	if not subscribed_users_df.empty:
		subscribed_users_dict = subscribed_users_df.T.to_dict()
		parse_date = str(datetime.now().date())
		for users in subscribed_users_dict.values():
			username = users['username']
			try:
				user_digest(username, parse_date, part_number)
			except ApiTelegramException as e:
				if e.description == "Forbidden: bot was blocked by the user":
					print(f"Пользователь {username} забанил бот.")
					asmi.execute(f"UPDATE user_settings SET is_subscribed = False WHERE username = '{username}'")


def run_bot():
	while True:
		try:
			bot.polling(none_stop=True)
		except Exception:
			pass


def run_sending_news():
	try:
		schedule.every().day.at("08:00").do(sending_news, 1)
		schedule.every().day.at("13:00").do(sending_news, 2)
		schedule.every().day.at("18:00").do(sending_news, 3)
		schedule.every().day.at("22:00").do(sending_news, 4)
	except json.JSONDecodeError:
		pass

	# Start cron task after some time interval
	while True:
		schedule.run_pending()
		time.sleep(1)


if __name__ == "__main__":
	try:
		bot_thread = threading.Thread(target=run_bot)
		sending_thread = threading.Thread(target=run_sending_news)

		bot_thread.start()
		sending_thread.start()
	except Exception:
		pass
