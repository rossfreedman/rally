--
-- PostgreSQL database dump
--

-- Dumped from database version 15.13 (Homebrew)
-- Dumped by pg_dump version 15.13 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_series_id_fkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_club_id_fkey;
ALTER TABLE IF EXISTS ONLY public.player_availability DROP CONSTRAINT IF EXISTS player_availability_series_id_fkey;
DROP INDEX IF EXISTS public.idx_user_instructions_email;
DROP INDEX IF EXISTS public.idx_user_email;
DROP INDEX IF EXISTS public.idx_user_activity_logs_user_email;
DROP INDEX IF EXISTS public.idx_player_availability;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_pkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_email_key;
ALTER TABLE IF EXISTS ONLY public.user_instructions DROP CONSTRAINT IF EXISTS user_instructions_pkey;
ALTER TABLE IF EXISTS ONLY public.user_activity_logs DROP CONSTRAINT IF EXISTS user_activity_logs_pkey;
ALTER TABLE IF EXISTS ONLY public.series DROP CONSTRAINT IF EXISTS series_pkey;
ALTER TABLE IF EXISTS ONLY public.series DROP CONSTRAINT IF EXISTS series_name_key;
ALTER TABLE IF EXISTS ONLY public.player_availability DROP CONSTRAINT IF EXISTS player_availability_player_name_match_date_series_id_key;
ALTER TABLE IF EXISTS ONLY public.player_availability DROP CONSTRAINT IF EXISTS player_availability_pkey;
ALTER TABLE IF EXISTS ONLY public.clubs DROP CONSTRAINT IF EXISTS clubs_pkey;
ALTER TABLE IF EXISTS ONLY public.clubs DROP CONSTRAINT IF EXISTS clubs_name_key;
ALTER TABLE IF EXISTS public.users ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.user_instructions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.user_activity_logs ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.series ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.player_availability ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.clubs ALTER COLUMN id DROP DEFAULT;
DROP SEQUENCE IF EXISTS public.users_id_seq;
DROP TABLE IF EXISTS public.users;
DROP SEQUENCE IF EXISTS public.user_instructions_id_seq;
DROP TABLE IF EXISTS public.user_instructions;
DROP SEQUENCE IF EXISTS public.user_activity_logs_id_seq;
DROP TABLE IF EXISTS public.user_activity_logs;
DROP SEQUENCE IF EXISTS public.series_id_seq;
DROP TABLE IF EXISTS public.series;
DROP SEQUENCE IF EXISTS public.player_availability_id_seq;
DROP TABLE IF EXISTS public.player_availability;
DROP SEQUENCE IF EXISTS public.clubs_id_seq;
DROP TABLE IF EXISTS public.clubs;
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: clubs; Type: TABLE; Schema: public; Owner: rossfreedman
--

CREATE TABLE public.clubs (
    id integer NOT NULL,
    name text NOT NULL
);


ALTER TABLE public.clubs OWNER TO rossfreedman;

--
-- Name: clubs_id_seq; Type: SEQUENCE; Schema: public; Owner: rossfreedman
--

CREATE SEQUENCE public.clubs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.clubs_id_seq OWNER TO rossfreedman;

--
-- Name: clubs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rossfreedman
--

ALTER SEQUENCE public.clubs_id_seq OWNED BY public.clubs.id;


--
-- Name: player_availability; Type: TABLE; Schema: public; Owner: rossfreedman
--

CREATE TABLE public.player_availability (
    id integer NOT NULL,
    player_name text NOT NULL,
    match_date date NOT NULL,
    is_available boolean DEFAULT true,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    series_id integer
);


ALTER TABLE public.player_availability OWNER TO rossfreedman;

--
-- Name: player_availability_id_seq; Type: SEQUENCE; Schema: public; Owner: rossfreedman
--

CREATE SEQUENCE public.player_availability_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.player_availability_id_seq OWNER TO rossfreedman;

--
-- Name: player_availability_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rossfreedman
--

ALTER SEQUENCE public.player_availability_id_seq OWNED BY public.player_availability.id;


--
-- Name: series; Type: TABLE; Schema: public; Owner: rossfreedman
--

CREATE TABLE public.series (
    id integer NOT NULL,
    name text NOT NULL
);


ALTER TABLE public.series OWNER TO rossfreedman;

--
-- Name: series_id_seq; Type: SEQUENCE; Schema: public; Owner: rossfreedman
--

CREATE SEQUENCE public.series_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.series_id_seq OWNER TO rossfreedman;

--
-- Name: series_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rossfreedman
--

ALTER SEQUENCE public.series_id_seq OWNED BY public.series.id;


--
-- Name: user_activity_logs; Type: TABLE; Schema: public; Owner: rossfreedman
--

CREATE TABLE public.user_activity_logs (
    id integer NOT NULL,
    user_email text NOT NULL,
    activity_type text NOT NULL,
    page text,
    action text,
    details text,
    ip_address text,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.user_activity_logs OWNER TO rossfreedman;

--
-- Name: user_activity_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: rossfreedman
--

CREATE SEQUENCE public.user_activity_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_activity_logs_id_seq OWNER TO rossfreedman;

--
-- Name: user_activity_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rossfreedman
--

ALTER SEQUENCE public.user_activity_logs_id_seq OWNED BY public.user_activity_logs.id;


--
-- Name: user_instructions; Type: TABLE; Schema: public; Owner: rossfreedman
--

CREATE TABLE public.user_instructions (
    id integer NOT NULL,
    user_email text NOT NULL,
    instruction text NOT NULL,
    series_id integer,
    team_id integer,
    created_at timestamp without time zone,
    series_name text,
    is_active boolean DEFAULT true,
    team_name text
);


ALTER TABLE public.user_instructions OWNER TO rossfreedman;

--
-- Name: user_instructions_id_seq; Type: SEQUENCE; Schema: public; Owner: rossfreedman
--

CREATE SEQUENCE public.user_instructions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_instructions_id_seq OWNER TO rossfreedman;

--
-- Name: user_instructions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rossfreedman
--

ALTER SEQUENCE public.user_instructions_id_seq OWNED BY public.user_instructions.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: rossfreedman
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email text NOT NULL,
    password_hash text NOT NULL,
    first_name text NOT NULL,
    last_name text NOT NULL,
    club_id integer,
    series_id integer,
    club_automation_password text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    last_login timestamp without time zone
);


ALTER TABLE public.users OWNER TO rossfreedman;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: rossfreedman
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO rossfreedman;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rossfreedman
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: clubs id; Type: DEFAULT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.clubs ALTER COLUMN id SET DEFAULT nextval('public.clubs_id_seq'::regclass);


--
-- Name: player_availability id; Type: DEFAULT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.player_availability ALTER COLUMN id SET DEFAULT nextval('public.player_availability_id_seq'::regclass);


--
-- Name: series id; Type: DEFAULT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.series ALTER COLUMN id SET DEFAULT nextval('public.series_id_seq'::regclass);


--
-- Name: user_activity_logs id; Type: DEFAULT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.user_activity_logs ALTER COLUMN id SET DEFAULT nextval('public.user_activity_logs_id_seq'::regclass);


--
-- Name: user_instructions id; Type: DEFAULT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.user_instructions ALTER COLUMN id SET DEFAULT nextval('public.user_instructions_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: clubs; Type: TABLE DATA; Schema: public; Owner: rossfreedman
--

COPY public.clubs (id, name) FROM stdin;
1	Tennaqua
2	Wilmette PD
3	Sunset Ridge
4	Winnetka
5	Exmoor
6	Hinsdale PC
7	Onwentsia
8	Salt Creek
9	Lakeshore S&F
10	Glen View
11	Prairie Club
12	Lake Forest
13	Evanston
14	Midt-Bannockburn
15	Briarwood
16	Birchwood
17	Hinsdale GC
18	Butterfield
19	Chicago Highlands
20	Glen Ellyn
21	Skokie
22	Winter Club
23	Westmoreland
24	Valley Lo
25	South Barrington
26	Saddle & Cycle
27	Ruth Lake
28	Northmoor
29	North Shore
30	Midtown - Chicago
31	Michigan Shores
32	Lake Shore CC
33	Knollwood
34	Indian Hill
35	Glenbrook RC
36	Hawthorn Woods
37	Lake Bluff
38	Barrington Hills CC
39	River Forest PD
40	Edgewood Valley
41	Park Ridge CC
42	Medinah
43	LaGrange CC
44	Dunham Woods
45	Bryn Mawr
46	Glen Oak
47	Inverness
48	White Eagle
49	Legends
50	River Forest CC
51	Oak Park CC
52	Royal Melbourne
105	Germantown Cricket Club
106	Philadelphia Cricket Club
107	Merion Cricket Club
108	Waynesborough Country Club
109	Aronimink Golf Club
110	Overbrook Golf Club
111	Radnor Valley Country Club
112	White Manor Country Club
\.


--
-- Data for Name: player_availability; Type: TABLE DATA; Schema: public; Owner: rossfreedman
--

COPY public.player_availability (id, player_name, match_date, is_available, updated_at, series_id) FROM stdin;
201	Ross Freedman	2024-10-08	f	2025-05-18 13:48:05.640834	22
200	Ross Freedman	2024-10-15	t	2025-05-18 13:48:07.116165	22
208	Ross Freedman	2024-10-22	t	2025-05-18 13:48:08.132539	22
202	Ross Freedman	2024-10-29	t	2025-05-18 13:48:09.612582	22
210	Ross Freedman	2024-11-12	f	2025-05-18 13:48:13.540345	22
199	Ross Freedman	2024-10-01	f	2025-05-18 13:56:23.887976	22
223	Adam Seyb	2024-09-24	t	2025-05-18 20:29:55.965947	22
224	Adam Seyb	2024-10-08	f	2025-05-18 20:29:57.995746	22
197	Ross Freedman	2024-09-24	t	2025-05-18 21:58:19.816531	22
\.


--
-- Data for Name: series; Type: TABLE DATA; Schema: public; Owner: rossfreedman
--

COPY public.series (id, name) FROM stdin;
1	Chicago 1
2	Chicago 2
3	Chicago 3
4	Chicago 4
5	Chicago 5
6	Chicago 6
7	Chicago 7
8	Chicago 8
9	Chicago 9
10	Chicago 10
11	Chicago 11
12	Chicago 12
13	Chicago 13
14	Chicago 14
15	Chicago 15
16	Chicago 16
17	Chicago 17
18	Chicago 18
19	Chicago 19
20	Chicago 20
21	Chicago 21
22	Chicago 22
23	Chicago 23
24	Chicago 24
25	Chicago 25
26	Chicago 26
27	Chicago 27
28	Chicago 28
29	Chicago 29
30	Chicago 30
31	Chicago 31
32	Chicago 32
33	Chicago 33
34	Chicago 34
35	Chicago 35
36	Chicago 36
37	Chicago 37
38	Chicago 38
39	Chicago 39
40	Chicago Legends
41	Chicago 7 SW
42	Chicago 9 SW
43	Chicago 11 SW
44	Chicago 13 SW
45	Chicago 15 SW
46	Chicago 17 SW
47	Chicago 19 SW
48	Chicago 21 SW
49	Chicago 23 SW
50	Chicago 25 SW
51	Chicago 27 SW
52	Chicago 29 SW
105	Series 1
106	Series 2
107	Series 3
108	Series 4
109	Series 5
110	Series 6
111	Series 7
112	Series 8
\.


--
-- Data for Name: user_activity_logs; Type: TABLE DATA; Schema: public; Owner: rossfreedman
--

COPY public.user_activity_logs (id, user_email, activity_type, page, action, details, ip_address, "timestamp") FROM stdin;
12512	rossfreedman@gmail.com	auth	\N	register	User registered successfully	127.0.0.1	2025-05-18 11:31:24.519266
12513	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 11:31:24.53512
12514	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 11:31:24.644658
12515	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 11:31:26.405018
12516	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 11:31:28.51398
12517	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 11:31:28.577514
12518	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 11:31:30.034995
12519	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 11:31:31.143947
12520	rossfreedman@gmail.com	auth	\N	login	Successful login	127.0.0.1	2025-05-18 11:31:38.287177
12521	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 11:31:38.30509
12522	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 11:31:38.368789
12523	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 11:31:39.400058
12524	rossfreedman@gmail.com	static_asset	favicon	\N	Accessed static asset: favicon.ico	127.0.0.1	2025-05-18 11:31:39.428312
12525	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 11:31:41.501289
12526	rossfreedman@gmail.com	auth	\N	login	Successful login	127.0.0.1	2025-05-18 12:08:07.433343
12527	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:08:07.456645
12528	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:08:07.563388
12529	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:08:08.850753
12530	rossfreedman@gmail.com	auth	\N	login	Successful login	127.0.0.1	2025-05-18 12:10:29.188096
12531	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:10:29.200547
12532	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:10:29.27409
12533	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:10:31.899906
12534	rossfreedman@gmail.com	auth	\N	login	Successful login	127.0.0.1	2025-05-18 12:10:50.538346
12535	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:10:50.552098
12536	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:10:50.60991
12537	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:10:54.746072
12538	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-05-18 12:10:54.834335
12539	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:10:54.927758
12540	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:10:57.557974
12541	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:10:58.258499
12542	rossfreedman@gmail.com	auth	\N	login	Successful login	127.0.0.1	2025-05-18 12:11:55.734712
12543	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:11:55.749997
12544	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:11:55.835183
12545	rossfreedman@gmail.com	auth	\N	login	Successful login	127.0.0.1	2025-05-18 12:16:59.72559
12546	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:16:59.743458
12547	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:16:59.853419
12548	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:17:00.858189
12549	rossfreedman@gmail.com	auth	\N	login	Successful login	127.0.0.1	2025-05-18 12:17:22.534051
12550	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:17:22.546584
12551	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:17:22.612911
12552	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:17:53.282488
12553	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-05-18 12:17:53.309826
12554	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:17:53.404079
12555	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:17:59.614214
12556	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:18:01.460754
12557	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:18:02.355208
12558	rossfreedman@gmail.com	auth	\N	login	Successful login	127.0.0.1	2025-05-18 12:19:41.571291
12559	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:19:41.588975
12560	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:19:41.677166
12561	rossfreedman@gmail.com	page_visit	\N	view_schedule	Viewed 71 matches	127.0.0.1	2025-05-18 12:19:42.539207
12562	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:19:42.538539
12563	rossfreedman@gmail.com	auth	\N	login	Successful login	127.0.0.1	2025-05-18 12:22:02.067652
12564	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:22:02.084003
12565	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:22:02.161017
12566	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:22:03.113668
12567	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:22:03.118334
12568	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:22:03.141732
12569	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:22:03.200663
12570	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:22:04.074152
12571	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:22:04.083143
12572	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:22:04.093604
12573	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:22:04.151156
12574	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:22:05.091584
12575	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:22:05.101545
12576	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:22:05.117704
12577	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:22:05.175332
12578	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:23:48.454225
12579	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:23:48.461313
12580	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:23:48.47206
12581	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:23:48.52114
12582	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:23:53.491883
12583	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:23:55.379268
12584	rossfreedman@gmail.com	auth	\N	login	Successful login	127.0.0.1	2025-05-18 12:27:02.426506
12585	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:27:02.443107
12586	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:27:02.535592
12588	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:27:03.587774
13757	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:08:18.29964
13760	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:08:18.386627
13763	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:08:19.134322
13766	rossfreedman@gmail.com	click	/mobile	button	button: 	127.0.0.1	2025-05-18 14:08:19.921075
13769	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:08:21.613574
13772	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:08:21.67366
13775	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:12:09.096709
13778	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:12:09.65748
13779	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:12:09.657367
13782	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:12:12.876896
13787	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 16:44:36.011488
13790	rossfreedman@gmail.com	click	/mobile/view-schedule	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 16:44:37.60608
13791	rossfreedman@gmail.com	click	/mobile/view-schedule	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 16:44:37.605979
13794	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 16:44:42.634298
13795	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 16:44:42.634229
13799	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 16:44:43.086564
13803	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 16:44:47.491367
13807	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 16:44:49.130921
13806	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 16:44:49.130973
13811	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 16:44:49.82576
13815	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 16:44:50.290719
13819	rossfreedman@gmail.com	click	/mobile/availability	a	a: Improve my game -> http://127.0.0.1:8080/mobile/improve	127.0.0.1	2025-05-18 16:46:28.260401
13821	rossfreedman@gmail.com	click	/mobile/improve	button	button: 	127.0.0.1	2025-05-18 16:46:29.09391
13825	rossfreedman@gmail.com	click	/mobile/improve	a	a: Logout -> http://127.0.0.1:8080/mobile/improve#	127.0.0.1	2025-05-18 16:46:41.257395
13828	rossfreedman@gmail.com	click	/mobile/improve	a	a: Logout -> http://127.0.0.1:8080/mobile/improve#	127.0.0.1	2025-05-18 16:47:10.037935
13830	rossfreedman@gmail.com	click	/mobile/improve	button	button: 	127.0.0.1	2025-05-18 16:48:11.333259
13834	rossfreedman@gmail.com	click	/mobile/improve	a	a: Improve my game -> http://127.0.0.1:8080/mobile/improve	127.0.0.1	2025-05-18 16:48:12.645374
13837	rossfreedman@gmail.com	click	/mobile/improve	a	a: My Club -> http://127.0.0.1:8080/mobile/my-club	127.0.0.1	2025-05-18 16:48:14.650645
13841	rossfreedman@gmail.com	click	/mobile/my-club	a	a: Logout -> http://127.0.0.1:8080/mobile/my-club#	127.0.0.1	2025-05-18 16:48:21.993746
13845	rossfreedman@gmail.com	click	/mobile/my-club	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 17:04:40.5098
13844	rossfreedman@gmail.com	click	/mobile/my-club	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 17:04:40.510017
13848	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 17:04:43.10392
13851	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 17:04:43.523972
13854	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 17:04:44.735381
13857	rossfreedman@gmail.com	click	/mobile	button	button: 	127.0.0.1	2025-05-18 17:04:48.571481
13860	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:04:51.46964
13864	rossfreedman@gmail.com	click	/mobile	a	a: Lineup Escrow -> http://127.0.0.1:8080/mobile/lineup-escrow	127.0.0.1	2025-05-18 17:04:52.288399
13867	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 17:06:20.550816
13870	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:06:24.151262
13871	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:06:24.150999
13874	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 17:07:04.119663
13879	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 17:07:07.214505
13878	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 17:07:07.214543
13883	rossfreedman@gmail.com	click	/mobile/availability	button	button: 	127.0.0.1	2025-05-18 17:08:15.611713
13885	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 17:08:18.20556
13890	rossfreedman@gmail.com	click	/mobile	button	button: 	127.0.0.1	2025-05-18 17:26:06.571177
13894	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:26:10.451767
13893	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:26:10.451715
13900	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:26:11.25193
13899	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:26:11.251878
13903	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:26:11.592955
13907	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 17:27:18.121574
12589	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:27:03.66169
12609	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:29:08.801451
12629	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:31:35.716173
12650	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:35:10.322789
12671	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:14.125919
12691	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:26.128411
12713	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:35.150153
12733	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:05.266397
12754	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:37:15.386789
12774	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:37:23.550343
12796	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 12:37:40.758748
12797	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:37:40.758786
12817	rossfreedman@gmail.com	click	/mobile	a	a: My Team -> http://127.0.0.1:8080/mobile/myteam	127.0.0.1	2025-05-18 12:38:33.292398
12837	rossfreedman@gmail.com	click	/mobile/analyze-me	page_visit	page_visit: Rally -> /mobile/analyze-me	127.0.0.1	2025-05-18 12:38:37.471969
12859	rossfreedman@gmail.com	click	/mobile/ask-ai	page_visit	page_visit: Rally -> /mobile/ask-ai	127.0.0.1	2025-05-18 12:38:53.426655
12880	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:42:07.966549
12902	rossfreedman@gmail.com	click	/mobile	a	a: Ask Rally AI -> http://127.0.0.1:8080/mobile/ask-ai	127.0.0.1	2025-05-18 12:42:11.698947
12921	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:44:21.465685
12942	rossfreedman@gmail.com	click	/mobile	a	a: My Team -> http://127.0.0.1:8080/mobile/myteam	127.0.0.1	2025-05-18 12:44:26.193029
12962	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:52:13.738152
12985	rossfreedman@gmail.com	click	/mobile/myteam	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:52:33.084474
13006	rossfreedman@gmail.com	click	/mobile/find-subs	page_visit	page_visit: Rally -> /mobile/find-subs	127.0.0.1	2025-05-18 12:52:49.269519
13027	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:57:06.536759
13048	rossfreedman@gmail.com	click	/mobile/improve	page_visit	page_visit: Rally -> /mobile/improve	127.0.0.1	2025-05-18 12:58:32.918905
13069	rossfreedman@gmail.com	click	/mobile/analyze-me	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 13:01:58.786576
13089	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:02:18.440668
13110	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:07:40.97572
13130	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:09:52.753783
13151	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:14:18.485536
13171	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:17:00.086647
13190	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:22:24.421992
13210	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:28:53.942608
13233	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:32:27.496791
13253	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:33:57.257474
13273	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:35:11.148576
13294	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:35:20.930492
13314	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:35:40.487175
13334	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:37:53.557274
13355	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:38:22.814252
13375	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:38:33.622361
13397	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:39:02.063426
13416	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:46:58.743098
13417	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:46:58.743417
13437	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:47:43.639717
13457	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:47:57.743521
13477	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:48:15.203155
13501	rossfreedman@gmail.com	click	/mobile	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:48:32.765199
13521	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:50:52.42348
13541	rossfreedman@gmail.com	click	/mobile/my-series	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 13:50:59.495388
13562	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:52:19.066578
13583	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:52:22.219135
13603	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:54:59.242536
13623	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:55:09.344688
13644	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:56:27.151625
13643	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 13:56:27.151593
13664	rossfreedman@gmail.com	click	/mobile/my-club	a	a: Logout -> http://127.0.0.1:8080/mobile/my-club#	127.0.0.1	2025-05-18 13:59:00.256604
13685	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:01:36.391237
13706	rossfreedman@gmail.com	click	/mobile/availability	button	button: 	127.0.0.1	2025-05-18 14:03:49.967989
12590	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:27:05.241655
12610	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:29:09.792896
12630	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:31:46.98078
12651	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:35:11.113028
12672	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:36:15.029584
12692	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Brian Rosenburg	127.0.0.1	2025-05-18 12:36:26.152887
12714	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:35.15463
12735	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:05.351205
12755	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:37:15.397071
12776	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:23.617188
12775	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:23.617195
12798	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:37:40.770687
12818	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:38:33.294856
12838	rossfreedman@gmail.com	click	/mobile/analyze-me	page_visit	page_visit: Rally -> /mobile/analyze-me	127.0.0.1	2025-05-18 12:38:37.471934
12860	rossfreedman@gmail.com	click	/mobile/ask-ai	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:38:54.484088
12883	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:42:08.082907
12903	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	Accessed Ask AI page	127.0.0.1	2025-05-18 12:42:11.698963
12922	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:44:22.002504
12943	rossfreedman@gmail.com	click	/mobile/myteam	page_visit	page_visit: Rally -> /mobile/myteam	127.0.0.1	2025-05-18 12:44:26.269977
12963	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 12:52:23.779837
12986	rossfreedman@gmail.com	click	/mobile	a	a: My Series -> http://127.0.0.1:8080/mobile/myseries	127.0.0.1	2025-05-18 12:52:33.93173
13007	rossfreedman@gmail.com	click	/mobile/find-subs	page_visit	page_visit: Rally -> /mobile/find-subs	127.0.0.1	2025-05-18 12:52:49.272194
13029	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:57:06.607054
13047	rossfreedman@gmail.com	click	/mobile/improve	page_visit	page_visit: Rally -> /mobile/improve	127.0.0.1	2025-05-18 12:58:32.918732
13070	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 13:01:59.384189
13090	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:04:31.81485
13111	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 13:07:41.323146
13131	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:09:56.098226
13152	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:14:18.485456
13172	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:17:00.549625
13192	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:22:24.427056
13212	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:28:53.947279
13234	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:32:28.154658
13254	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 13:33:57.764727
13274	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:35:11.152109
13295	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:35:20.930467
13315	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:35:40.489675
13335	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:37:53.754515
13356	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:38:23.556378
13377	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:38:33.627204
13396	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:39:02.063193
13418	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:46:58.747614
13438	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/01/2024, Available: True	127.0.0.1	2025-05-18 13:47:43.649252
13458	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:47:57.905839
13478	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:48:15.203127
13500	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:48:32.765254
13523	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:50:52.428595
13542	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	127.0.0.1	2025-05-18 13:51:01.199079
13563	rossfreedman@gmail.com	click	/mobile	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:52:19.069901
13584	rossfreedman@gmail.com	static_asset	com.chrome.devtools	\N	Accessed static asset: .well-known/appspecific/com.chrome.devtools.json	127.0.0.1	2025-05-18 13:52:35.698563
13604	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:54:59.37654
13624	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:55:09.344594
13645	rossfreedman@gmail.com	auth	\N	logout	\N	127.0.0.1	2025-05-18 13:56:27.151545
13665	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:59:00.308444
13687	rossfreedman@gmail.com	auth	\N	logout	\N	127.0.0.1	2025-05-18 14:01:36.391221
13708	rossfreedman@gmail.com	auth	\N	logout	\N	127.0.0.1	2025-05-18 14:03:51.714225
13707	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 14:03:51.714192
13709	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:03:51.714145
13726	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:05:05.447138
12591	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:27:06.028139
12611	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:29:10.581112
12631	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:31:47.100747
12652	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:35:11.694382
12673	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:15.037999
12693	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:26.243674
12715	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:36:46.715002
12736	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:05.35109
12756	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:15.460959
12777	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:23.621253
12799	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:37:40.830387
12820	rossfreedman@gmail.com	click	/mobile/myteam	page_visit	page_visit: Rally -> /mobile/myteam	127.0.0.1	2025-05-18 12:38:33.366889
12839	rossfreedman@gmail.com	click	/mobile/analyze-me	page_visit	page_visit: Rally -> /mobile/analyze-me	127.0.0.1	2025-05-18 12:38:37.475959
12861	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:38:56.600826
12881	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:42:08.082963
12901	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:42:11.699201
12923	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 12:44:22.003246
12944	rossfreedman@gmail.com	click	/mobile/myteam	page_visit	page_visit: Rally -> /mobile/myteam	127.0.0.1	2025-05-18 12:44:26.269925
12964	rossfreedman@gmail.com	static_asset	favicon	\N	Accessed static asset: favicon.ico	127.0.0.1	2025-05-18 12:52:23.812583
12987	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	127.0.0.1	2025-05-18 12:52:33.934966
13008	rossfreedman@gmail.com	click	/mobile/find-subs	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:52:50.352637
13028	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:57:06.607072
13049	rossfreedman@gmail.com	click	/mobile/improve	page_visit	page_visit: Rally -> /mobile/improve	127.0.0.1	2025-05-18 12:58:32.922463
13071	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 13:01:59.388947
13091	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:04:31.814826
13112	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 13:07:41.325365
13132	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:09:56.098758
13153	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:14:18.490018
13173	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:17:00.556776
13193	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:22:25.870652
13213	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:28:55.021119
13235	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:32:28.162662
13255	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 13:33:57.768221
13275	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:35:11.23647
13276	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:35:11.236447
13296	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:35:20.934053
13316	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:35:40.564083
13336	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:37:53.754503
13357	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: False	127.0.0.1	2025-05-18 13:38:23.564461
13378	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:38:34.327304
13398	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:39:02.136143
13419	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:46:59.776425
13439	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:47:46.032504
13459	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:47:57.910893
13480	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:48:15.275695
13479	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:48:15.275703
13502	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:48:32.82609
13522	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:50:52.428711
13543	rossfreedman@gmail.com	click	/mobile	a	a: Create Lineup -> http://127.0.0.1:8080/mobile/lineup	127.0.0.1	2025-05-18 13:51:01.205765
13564	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:52:19.135653
13585	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:54:24.04845
13605	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:54:59.376474
13625	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:55:09.345755
13647	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:56:27.220387
13666	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:59:00.308436
13686	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 14:01:36.391171
13710	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:03:51.780672
13727	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:05:05.505896
13739	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:06:14.67498
13748	rossfreedman@gmail.com	click	/mobile/myteam	page_visit	page_visit: Rally -> /mobile/myteam	127.0.0.1	2025-05-18 14:06:16.298932
12592	rossfreedman@gmail.com	auth	\N	login	Successful login	127.0.0.1	2025-05-18 12:28:59.065739
12612	rossfreedman@gmail.com	auth	\N	login	Successful login	127.0.0.1	2025-05-18 12:30:08.568772
12632	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:31:48.247046
12653	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:35:11.694389
12675	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:15.112057
12694	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:26.243647
12716	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:46.721333
12737	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:05.351001
12757	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:15.462216
12778	rossfreedman@gmail.com	click	/mobile	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 12:37:38.928571
12779	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:37:38.928061
12800	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:37:40.830872
12819	rossfreedman@gmail.com	click	/mobile/myteam	page_visit	page_visit: Rally -> /mobile/myteam	127.0.0.1	2025-05-18 12:38:33.366729
12840	rossfreedman@gmail.com	click	/mobile/analyze-me	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:38:39.435629
12862	rossfreedman@gmail.com	click	/mobile	a	a: Improve my game -> http://127.0.0.1:8080/mobile/improve	127.0.0.1	2025-05-18 12:38:56.604953
12882	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:42:08.082939
12904	rossfreedman@gmail.com	click	/mobile/ask-ai	page_visit	page_visit: Rally -> /mobile/ask-ai	127.0.0.1	2025-05-18 12:42:11.768171
12924	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:44:22.025059
12945	rossfreedman@gmail.com	click	/mobile/myteam	page_visit	page_visit: Rally -> /mobile/myteam	127.0.0.1	2025-05-18 12:44:26.274126
12965	rossfreedman@gmail.com	click	/mobile	a	a: Improve my game -> http://127.0.0.1:8080/mobile/improve	127.0.0.1	2025-05-18 12:52:25.778816
12966	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	127.0.0.1	2025-05-18 12:52:25.778839
12988	rossfreedman@gmail.com	click	/mobile/my-series	page_visit	page_visit: Rally -> /mobile/my-series	127.0.0.1	2025-05-18 12:52:34.013581
13009	rossfreedman@gmail.com	click	/mobile	a	a: Create Lineup -> http://127.0.0.1:8080/mobile/lineup	127.0.0.1	2025-05-18 12:52:51.367813
13030	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:57:06.610684
13050	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	127.0.0.1	2025-05-18 12:59:46.886988
13072	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:01:59.476775
13092	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:04:31.818953
13114	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:07:41.411198
13133	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:09:56.173645
13154	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:14:19.458762
13174	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:18:12.915016
13194	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:22:25.874138
13214	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:28:55.025481
13237	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:33:51.531812
13256	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:33:57.855026
13277	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:35:11.240567
13297	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:35:21.740346
13317	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:35:40.564039
13337	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:37:53.762279
13358	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:38:25.395928
13379	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:38:34.484683
13399	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:39:02.136212
13420	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:46:59.779941
13440	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:47:46.037954
13460	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:47:57.910858
13481	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:48:15.278306
13503	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:48:32.826083
13524	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:50:54.164553
13544	rossfreedman@gmail.com	click	/mobile/lineup	page_visit	page_visit: Rally -> /mobile/lineup	127.0.0.1	2025-05-18 13:51:01.279281
13565	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:52:19.135665
13586	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:54:24.123849
13606	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:54:59.383053
13626	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:56:17.953842
13646	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:56:27.220418
13667	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:59:00.311716
13688	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:01:36.447584
13689	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:01:36.447544
13711	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:03:51.780837
13728	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:05:05.505825
12593	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:28:59.082925
12613	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:30:08.581511
12633	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:31:48.274348
12654	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:35:11.703297
12674	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:15.11178
12695	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:26.248079
12717	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:36:57.097886
12738	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:07.483994
12758	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:15.463587
12780	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:37:38.930024
12801	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:37:40.833754
12821	rossfreedman@gmail.com	click	/mobile/myteam	page_visit	page_visit: Rally -> /mobile/myteam	127.0.0.1	2025-05-18 12:38:33.377774
12842	rossfreedman@gmail.com	click	/mobile	a	a: My Club -> http://127.0.0.1:8080/mobile/my-club	127.0.0.1	2025-05-18 12:38:40.351256
12863	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	127.0.0.1	2025-05-18 12:38:56.605973
12884	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:42:08.635036
12905	rossfreedman@gmail.com	click	/mobile/ask-ai	page_visit	page_visit: Rally -> /mobile/ask-ai	127.0.0.1	2025-05-18 12:42:11.767906
12925	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:44:22.088777
12946	rossfreedman@gmail.com	click	/mobile/myteam	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:44:27.107136
12967	rossfreedman@gmail.com	click	/mobile/improve	page_visit	page_visit: Rally -> /mobile/improve	127.0.0.1	2025-05-18 12:52:25.867807
12989	rossfreedman@gmail.com	click	/mobile/my-series	page_visit	page_visit: Rally -> /mobile/my-series	127.0.0.1	2025-05-18 12:52:34.01506
13010	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	127.0.0.1	2025-05-18 12:52:51.367745
13031	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 12:57:07.304132
13053	rossfreedman@gmail.com	click	/mobile/improve	page_visit	page_visit: Rally -> /mobile/improve	127.0.0.1	2025-05-18 12:59:46.972117
13051	rossfreedman@gmail.com	click	/mobile/improve	page_visit	page_visit: Rally -> /mobile/improve	127.0.0.1	2025-05-18 12:59:46.972119
13073	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:01:59.476692
13093	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:04:34.98885
13113	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:07:41.410479
13134	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:09:56.173557
13155	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:14:19.464185
13176	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:18:12.921261
13195	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:23:34.444943
13215	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:29:47.71688
13216	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:29:47.716989
13236	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:33:51.531522
13257	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:33:57.855029
13278	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 13:35:12.213428
13298	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:35:21.911448
13318	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:35:40.564109
13338	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:37:54.383664
13359	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/08/2024, Available: False	127.0.0.1	2025-05-18 13:38:25.402098
13380	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:38:34.484677
13400	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:39:02.141659
13421	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:47:13.875327
13441	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:47:46.103218
13461	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:48:02.183352
13482	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:48:15.991387
13504	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:48:32.829874
13525	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:50:54.174532
13545	rossfreedman@gmail.com	click	/mobile/lineup	page_visit	page_visit: Rally -> /mobile/lineup	127.0.0.1	2025-05-18 13:51:01.285145
13566	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:52:19.139176
13587	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:54:24.123805
13607	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:55:01.226454
13627	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:56:17.953849
13648	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:56:27.225405
13668	rossfreedman@gmail.com	static_asset	com.chrome.devtools	\N	Accessed static asset: .well-known/appspecific/com.chrome.devtools.json	127.0.0.1	2025-05-18 13:59:24.98425
13690	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:01:36.45163
13712	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:03:51.78359
12594	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:28:59.184261
12614	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:30:08.667542
12634	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:31:48.333136
12655	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:35:11.724721
12676	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:15.113883
12696	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:27.386971
12719	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	127.0.0.1	2025-05-18 12:36:57.099794
12739	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:37:08.64381
12759	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:18.324629
12781	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:37:39.013271
12802	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:37:41.202467
12822	rossfreedman@gmail.com	click	/mobile/myteam	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:38:34.622913
12841	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:38:40.350962
12864	rossfreedman@gmail.com	click	/mobile/improve	page_visit	page_visit: Rally -> /mobile/improve	127.0.0.1	2025-05-18 12:38:56.67275
12885	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 12:42:08.650483
12906	rossfreedman@gmail.com	click	/mobile/ask-ai	page_visit	page_visit: Rally -> /mobile/ask-ai	127.0.0.1	2025-05-18 12:42:11.771383
12926	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:44:22.088732
12947	rossfreedman@gmail.com	click	/mobile	a	a: Me -> http://127.0.0.1:8080/mobile/analyze-me	127.0.0.1	2025-05-18 12:44:28.16712
12968	rossfreedman@gmail.com	click	/mobile/improve	page_visit	page_visit: Rally -> /mobile/improve	127.0.0.1	2025-05-18 12:52:25.869108
12990	rossfreedman@gmail.com	click	/mobile/my-series	page_visit	page_visit: Rally -> /mobile/my-series	127.0.0.1	2025-05-18 12:52:34.019058
13011	rossfreedman@gmail.com	click	/mobile/lineup	page_visit	page_visit: Rally -> /mobile/lineup	127.0.0.1	2025-05-18 12:52:51.439524
13032	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:57:07.306279
13052	rossfreedman@gmail.com	click	/mobile/improve	page_visit	page_visit: Rally -> /mobile/improve	127.0.0.1	2025-05-18 12:59:46.972078
13074	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:01:59.480283
13094	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:04:35.003003
13115	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:07:41.413818
13135	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:09:56.177743
13156	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:15:48.307815
13175	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:18:12.921146
13196	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:23:34.44507
13217	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:29:47.720526
13238	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:33:51.538262
13258	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:33:57.858844
13279	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 13:35:12.219779
13299	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:35:21.911423
13319	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:35:41.475168
13339	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: False	127.0.0.1	2025-05-18 13:37:54.391246
13361	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:38:28.130588
13381	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:38:34.486659
13401	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:39:04.398783
13422	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:47:13.875333
13442	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:47:46.102795
13462	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/01/2024, Available: False	127.0.0.1	2025-05-18 13:48:02.193145
13483	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:48:16.150753
13506	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:48:33.281423
13526	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:50:54.870222
13546	rossfreedman@gmail.com	click	/mobile/lineup	page_visit	page_visit: Rally -> /mobile/lineup	127.0.0.1	2025-05-18 13:51:01.289318
13567	rossfreedman@gmail.com	click	/mobile	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:52:19.400299
13588	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:54:24.125195
13608	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:55:01.42657
13628	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:56:17.958854
13649	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:58:49.58916
13670	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:01:30.710108
13691	rossfreedman@gmail.com	static_asset	com.chrome.devtools	\N	Accessed static asset: .well-known/appspecific/com.chrome.devtools.json	127.0.0.1	2025-05-18 14:01:44.418287
13713	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:05:00.79782
13729	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:05:05.509338
13740	rossfreedman@gmail.com	click	/mobile	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 14:06:14.848885
13749	rossfreedman@gmail.com	click	/mobile/myteam	button	button: 	127.0.0.1	2025-05-18 14:06:17.438858
12595	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:29:00.276398
12615	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:30:09.544629
12635	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:33:55.013301
12656	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:35:12.370341
12677	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:16.680592
12697	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:29.94836
12718	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:57.099855
12740	rossfreedman@gmail.com	page_visit	mobile_lineup_escrow	\N	Accessed mobile lineup escrow page	127.0.0.1	2025-05-18 12:37:08.646097
12760	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:18.324819
12782	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:37:39.013273
12803	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 12:37:41.220786
12823	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:38:34.632394
12843	rossfreedman@gmail.com	click	/mobile/my-club	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:38:45.814944
12865	rossfreedman@gmail.com	click	/mobile/improve	page_visit	page_visit: Rally -> /mobile/improve	127.0.0.1	2025-05-18 12:38:56.67275
12886	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:42:08.65819
12907	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:42:13.255151
12927	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:44:22.091735
12948	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-05-18 12:44:28.193759
12969	rossfreedman@gmail.com	click	/mobile/improve	page_visit	page_visit: Rally -> /mobile/improve	127.0.0.1	2025-05-18 12:52:25.870053
12991	rossfreedman@gmail.com	click	/mobile/my-series	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:52:34.967108
13012	rossfreedman@gmail.com	click	/mobile/lineup	page_visit	page_visit: Rally -> /mobile/lineup	127.0.0.1	2025-05-18 12:52:51.439442
13033	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:57:07.317997
13054	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:59:47.867088
13075	rossfreedman@gmail.com	click	/mobile/view-schedule	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 13:02:02.88966
13095	rossfreedman@gmail.com	static_asset	com.chrome.devtools	\N	Accessed static asset: .well-known/appspecific/com.chrome.devtools.json	127.0.0.1	2025-05-18 13:05:07.969211
13116	rossfreedman@gmail.com	click	/mobile/view-schedule	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 13:07:42.873435
13137	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:09:56.562401
13136	rossfreedman@gmail.com	click	/mobile	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:09:56.562398
13157	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:15:48.422601
13177	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:18:13.787505
13197	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:23:34.448252
13218	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:29:48.551127
13239	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:33:52.452187
13259	rossfreedman@gmail.com	click	/mobile/view-schedule	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 13:33:59.30815
13281	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:35:12.304143
13300	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:35:21.914619
13320	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:35:41.649283
13340	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:37:56.375119
13360	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:38:28.130656
13382	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:38:49.331812
13402	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:39:04.566137
13424	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:47:13.935886
13443	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:47:46.106147
13463	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:48:05.61896
13484	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:48:16.150741
13505	rossfreedman@gmail.com	click	/mobile	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:48:33.281551
13527	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/01/2024, Available: True	127.0.0.1	2025-05-18 13:50:54.880102
13547	rossfreedman@gmail.com	click	/mobile/lineup	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 13:51:02.281429
13568	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:52:19.400354
13589	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:54:25.465941
13609	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:55:01.42701
13629	rossfreedman@gmail.com	click	/mobile/availability	button	button: 	127.0.0.1	2025-05-18 13:56:19.049741
13651	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:58:49.663051
13669	rossfreedman@gmail.com	click	/mobile	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 14:01:30.71009
13692	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:03:44.094075
13714	rossfreedman@gmail.com	click	/mobile	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 14:05:00.801614
13730	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:06:14.272652
13741	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:06:14.848908
13752	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:06:18.807334
13784	rossfreedman@gmail.com	auth	\N	logout	\N	127.0.0.1	2025-05-18 14:12:12.883826
12596	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:29:00.285173
12616	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:30:09.548892
12636	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:33:55.077232
12657	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:35:12.372342
12678	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:36:17.532751
12698	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:30.401456
12721	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:57.171943
12741	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:08.646601
12761	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:18.326062
12783	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:37:39.017823
12804	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:37:41.22606
12824	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:38:34.71142
12844	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:38:49.355835
12866	rossfreedman@gmail.com	click	/mobile/improve	page_visit	page_visit: Rally -> /mobile/improve	127.0.0.1	2025-05-18 12:38:56.675426
12887	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:42:08.680754
12909	rossfreedman@gmail.com	click	/mobile	a	a: Improve my game -> http://127.0.0.1:8080/mobile/improve	127.0.0.1	2025-05-18 12:42:13.259544
12928	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 12:44:22.727685
12949	rossfreedman@gmail.com	click	/mobile/analyze-me	page_visit	page_visit: Rally -> /mobile/analyze-me	127.0.0.1	2025-05-18 12:44:28.268997
12970	rossfreedman@gmail.com	click	/mobile	a	a: Ask Rally AI -> http://127.0.0.1:8080/mobile/ask-ai	127.0.0.1	2025-05-18 12:52:27.931593
12971	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	Accessed Ask AI page	127.0.0.1	2025-05-18 12:52:27.931544
12992	rossfreedman@gmail.com	click	/mobile	a	a: My Club -> http://127.0.0.1:8080/mobile/my-club	127.0.0.1	2025-05-18 12:52:35.569459
13013	rossfreedman@gmail.com	click	/mobile/lineup	page_visit	page_visit: Rally -> /mobile/lineup	127.0.0.1	2025-05-18 12:52:51.44744
13034	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:57:07.371761
13055	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:59:47.937909
13056	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:59:47.937787
13076	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 13:02:03.849056
13096	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:06:21.086168
13117	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:07:43.499798
13138	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:09:56.632702
13158	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:15:48.422585
13178	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:18:13.78917
13198	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:23:35.475861
13219	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:29:48.560778
13240	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:33:52.458206
13260	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:33:59.854106
13280	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:35:12.304236
13301	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:35:25.191709
13321	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:35:41.649248
13341	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/08/2024, Available: False	127.0.0.1	2025-05-18 13:37:56.3808
13362	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:38:28.202744
13383	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: False	127.0.0.1	2025-05-18 13:38:49.341237
13403	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:39:04.566155
13423	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:47:13.935851
13444	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:47:47.298292
13464	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/08/2024, Available: False	127.0.0.1	2025-05-18 13:48:05.628393
13485	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:48:16.157218
13507	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:48:33.333508
13528	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:50:55.360871
13548	rossfreedman@gmail.com	click	/mobile	button	button: 	127.0.0.1	2025-05-18 13:51:03.164402
13570	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:52:19.485174
13591	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:54:25.643419
13610	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:55:01.42756
13630	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 13:56:20.487644
13650	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:58:49.66307
13672	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:01:30.815615
13693	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:03:44.165884
13715	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:05:00.880906
13731	rossfreedman@gmail.com	click	/mobile	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 14:06:14.273791
12597	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:29:00.309828
12617	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:30:09.569386
12637	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:33:55.722275
12658	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:35:12.378047
12679	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	127.0.0.1	2025-05-18 12:36:17.535074
12700	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:31.759814
12720	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:57.171973
12742	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:08.718503
12762	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:37:18.975463
12784	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:37:39.53015
12805	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:37:41.23693
12825	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:38:34.711398
12845	rossfreedman@gmail.com	click	/mobile	a	a: My Competition -> http://127.0.0.1:8080/mobile/teams-players	127.0.0.1	2025-05-18 12:38:49.364739
12867	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:38:58.503126
12868	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:38:58.50312
12889	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:42:08.742751
12908	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	127.0.0.1	2025-05-18 12:42:13.259046
12929	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:44:22.735855
12950	rossfreedman@gmail.com	click	/mobile/analyze-me	page_visit	page_visit: Rally -> /mobile/analyze-me	127.0.0.1	2025-05-18 12:44:28.269031
12973	rossfreedman@gmail.com	click	/mobile/ask-ai	page_visit	page_visit: Rally -> /mobile/ask-ai	127.0.0.1	2025-05-18 12:52:27.995914
12993	rossfreedman@gmail.com	click	/mobile/my-club	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:52:36.513276
13014	rossfreedman@gmail.com	click	/mobile/lineup	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:52:53.299112
13035	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:57:07.371753
13057	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:59:47.940536
13077	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 13:02:03.852016
13097	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:06:21.086173
13118	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:07:43.659516
13140	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:09:56.634432
13159	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:15:48.426584
13179	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:19:43.361726
13199	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:23:35.483775
13220	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:30:55.916188
13221	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:30:55.916155
13241	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: False	127.0.0.1	2025-05-18 13:33:53.40108
13261	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:34:00.01316
13282	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:35:12.308077
13302	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: False	127.0.0.1	2025-05-18 13:35:25.199844
13322	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:35:41.649918
13342	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 13:37:59.785029
13363	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:38:28.202573
13384	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:38:50.180227
13404	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:39:04.571309
13425	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:47:13.940458
13445	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:47:47.46797
13465	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:48:06.645489
13486	rossfreedman@gmail.com	click	/mobile/availability	button	button: 	127.0.0.1	2025-05-18 13:48:25.678522
13508	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:48:33.334107
13529	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: False	127.0.0.1	2025-05-18 13:50:55.372463
13549	rossfreedman@gmail.com	auth	\N	logout	\N	127.0.0.1	2025-05-18 13:51:04.742733
13569	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:52:19.485206
13590	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:54:25.643365
13611	rossfreedman@gmail.com	click	/mobile/availability	button	button: 	127.0.0.1	2025-05-18 13:55:01.970803
13632	rossfreedman@gmail.com	auth	\N	logout	\N	127.0.0.1	2025-05-18 13:56:20.489469
13652	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:58:49.664835
13671	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:01:30.815636
13694	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:03:44.165914
13716	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:05:00.88088
13733	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:06:14.337333
13742	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:06:14.90673
12598	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:29:00.371258
12618	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:30:09.628701
12638	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:33:55.798607
12659	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:35:12.38881
12680	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:17.539259
12699	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:36:31.759825
12722	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:57.176351
12743	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:08.718453
12763	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:19.033497
12785	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:37:39.877036
12807	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:37:41.297325
12826	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:38:34.71709
12846	rossfreedman@gmail.com	click	/mobile/teams-players	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:38:50.81964
12869	rossfreedman@gmail.com	click	/mobile/improve	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 12:38:58.504344
12888	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:42:08.742742
12911	rossfreedman@gmail.com	click	/mobile/improve	page_visit	page_visit: Rally -> /mobile/improve	127.0.0.1	2025-05-18 12:42:13.331813
12930	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:44:22.746537
12951	rossfreedman@gmail.com	click	/mobile/analyze-me	page_visit	page_visit: Rally -> /mobile/analyze-me	127.0.0.1	2025-05-18 12:44:28.272226
12972	rossfreedman@gmail.com	click	/mobile/ask-ai	page_visit	page_visit: Rally -> /mobile/ask-ai	127.0.0.1	2025-05-18 12:52:27.995927
12994	rossfreedman@gmail.com	click	/mobile	a	a: My Competition -> http://127.0.0.1:8080/mobile/teams-players	127.0.0.1	2025-05-18 12:52:37.383698
13015	rossfreedman@gmail.com	click	/mobile	a	a: Lineup Escrow -> http://127.0.0.1:8080/mobile/lineup-escrow	127.0.0.1	2025-05-18 12:52:54.105853
13036	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:57:07.375508
13058	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 12:59:48.778882
13078	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:02:03.925545
13098	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:06:21.090583
13119	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:07:43.661325
13139	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:09:56.634363
13160	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:15:49.335302
13180	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:19:43.361747
13200	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:26:37.491595
13222	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:30:55.920713
13242	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:33:53.407129
13262	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:34:00.016217
13283	rossfreedman@gmail.com	click	/mobile/view-schedule	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 13:35:13.59005
13303	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:35:26.964589
13323	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 13:36:43.758216
13343	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:38:00.6641
13364	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:38:28.205558
13385	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/01/2024, Available: False	127.0.0.1	2025-05-18 13:38:50.188757
13405	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:39:16.492039
13426	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:47:14.548308
13446	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:47:47.46796
13466	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/15/2024, Available: False	127.0.0.1	2025-05-18 13:48:06.658376
13488	rossfreedman@gmail.com	auth	\N	logout	\N	127.0.0.1	2025-05-18 13:48:27.964477
13509	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:48:33.33654
13530	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 13:50:56.31648
13550	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 13:51:04.742701
13571	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:52:19.489316
13592	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:54:25.646924
13612	rossfreedman@gmail.com	click	/mobile/availability	button	button: 	127.0.0.1	2025-05-18 13:55:02.568852
13631	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:56:20.489509
13653	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:58:52.834329
13673	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:01:30.818274
13695	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:03:44.171373
13717	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:05:00.886143
13732	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:06:14.337263
13743	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:06:14.907134
13750	rossfreedman@gmail.com	click	/mobile/myteam	a	a: Logout -> http://127.0.0.1:8080/mobile/myteam#	127.0.0.1	2025-05-18 14:06:18.807414
12599	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:29:01.903372
12619	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:30:28.079768
12639	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:33:56.263627
12661	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:35:12.813423
12660	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:35:12.81355
12682	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:17.607438
12701	rossfreedman@gmail.com	static_asset	favicon	\N	Accessed static asset: favicon.ico	127.0.0.1	2025-05-18 12:36:31.791605
12723	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:59.244083
12744	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:08.722828
12764	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:19.033367
12786	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:37:39.879419
12806	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:37:41.297283
12827	rossfreedman@gmail.com	click	/mobile	a	a: My Series -> http://127.0.0.1:8080/mobile/myseries	127.0.0.1	2025-05-18 12:38:35.501317
12847	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:38:51.820914
12870	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:38:58.574967
12890	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:42:08.746175
12910	rossfreedman@gmail.com	click	/mobile/improve	page_visit	page_visit: Rally -> /mobile/improve	127.0.0.1	2025-05-18 12:42:13.331808
12931	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:44:22.816502
12932	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:44:22.816568
12952	rossfreedman@gmail.com	click	/mobile/analyze-me	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:44:29.255104
12974	rossfreedman@gmail.com	click	/mobile/ask-ai	page_visit	page_visit: Rally -> /mobile/ask-ai	127.0.0.1	2025-05-18 12:52:27.998398
12995	rossfreedman@gmail.com	click	/mobile/teams-players	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:52:39.805813
13016	rossfreedman@gmail.com	page_visit	mobile_lineup_escrow	\N	Accessed mobile lineup escrow page	127.0.0.1	2025-05-18 12:52:54.10891
13037	rossfreedman@gmail.com	static_asset	com.chrome.devtools	\N	Accessed static asset: .well-known/appspecific/com.chrome.devtools.json	127.0.0.1	2025-05-18 12:57:19.767958
13059	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:59:48.783062
13079	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:02:03.925577
13099	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:06:22.408475
13120	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:07:43.662399
13141	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:09:57.217389
13162	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:15:49.502312
13181	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:19:43.365856
13201	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:26:37.491807
13223	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:30:56.599383
13243	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:33:54.278641
13263	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:34:00.017263
13284	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:35:14.387294
13304	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:35:26.966807
13324	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 13:36:44.38017
13344	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:38:00.837296
13365	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:38:29.418745
13386	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:38:51.349298
13406	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: False	127.0.0.1	2025-05-18 13:39:16.501271
13428	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:47:14.707409
13447	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:47:47.472973
13467	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:48:07.088349
13487	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 13:48:27.96425
13510	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:50:49.706464
13531	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:50:56.995705
13551	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:51:04.744522
13572	rossfreedman@gmail.com	click	/mobile	a	a: Ask Rally AI -> http://127.0.0.1:8080/mobile/ask-ai	127.0.0.1	2025-05-18 13:52:20.135849
13573	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	Accessed Ask AI page	127.0.0.1	2025-05-18 13:52:20.136066
13593	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:54:26.395977
13613	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:55:03.42046
13633	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:56:20.571639
13654	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:58:53.047204
13674	rossfreedman@gmail.com	click	/mobile	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 14:01:31.104192
13675	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:01:31.104253
12601	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	127.0.0.1	2025-05-18 12:29:03.726184
12620	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:30:28.087428
12640	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:33:56.276412
12662	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:35:12.823115
12681	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:17.607408
12702	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:36:33.598826
12724	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:37:00.095402
12745	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:09.900958
12765	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:19.0359
12787	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:37:39.879372
12808	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:37:41.301206
12828	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:38:35.501351
12848	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:38:51.844316
12871	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:38:58.574765
12891	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:42:09.474799
12912	rossfreedman@gmail.com	click	/mobile/improve	page_visit	page_visit: Rally -> /mobile/improve	127.0.0.1	2025-05-18 12:42:13.3343
12933	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:44:22.819988
12953	rossfreedman@gmail.com	click	/mobile	a	a: My Series -> http://127.0.0.1:8080/mobile/myseries	127.0.0.1	2025-05-18 12:44:29.859256
12975	rossfreedman@gmail.com	click	/mobile	a	a: Me -> http://127.0.0.1:8080/mobile/analyze-me	127.0.0.1	2025-05-18 12:52:30.576008
12996	rossfreedman@gmail.com	click	/mobile/teams-players	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:52:40.965175
13018	rossfreedman@gmail.com	click	/mobile/lineup-escrow	page_visit	page_visit: Lineup Escrow™ | Rally -> /mobile/lineup-escrow	127.0.0.1	2025-05-18 12:52:54.165078
13017	rossfreedman@gmail.com	click	/mobile/lineup-escrow	page_visit	page_visit: Lineup Escrow™ | Rally -> /mobile/lineup-escrow	127.0.0.1	2025-05-18 12:52:54.165088
13038	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	127.0.0.1	2025-05-18 12:58:27.314319
13060	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:59:48.813812
13080	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:02:03.927446
13100	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:06:22.413516
13121	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:07:44.602861
13142	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:09:57.375219
13161	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:15:49.501895
13182	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:19:44.319947
13202	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:26:37.493847
13224	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:30:56.599496
13244	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:33:54.284663
13264	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:34:01.096231
13285	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:35:14.57655
13305	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:35:27.035541
13325	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 13:36:44.38402
13345	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:38:00.837277
13367	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:38:29.590998
13387	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/15/2024, Available: True	127.0.0.1	2025-05-18 13:38:51.3629
13408	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:39:18.953861
13427	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:47:14.707709
13448	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:47:50.317764
13468	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/15/2024, Available: True	127.0.0.1	2025-05-18 13:48:07.099028
13489	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:48:27.967079
13511	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:50:49.823576
13532	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:50:57.1521
13552	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:51:04.801585
13574	rossfreedman@gmail.com	click	/mobile/ask-ai	page_visit	page_visit: Rally -> /mobile/ask-ai	127.0.0.1	2025-05-18 13:52:20.207372
13594	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:54:26.4063
13614	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: False	127.0.0.1	2025-05-18 13:55:03.429666
13634	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:56:20.573331
13655	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:58:53.047184
13676	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:01:31.177964
13696	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 14:03:45.167282
13718	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:05:01.31362
12600	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:29:03.726148
12621	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:30:28.099899
12641	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:33:56.286122
12663	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:35:12.835494
12683	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:17.60953
12703	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	Accessed Ask AI page	127.0.0.1	2025-05-18 12:36:33.605867
12704	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:33.605824
12725	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:00.108817
12746	rossfreedman@gmail.com	static_asset	reserve-court	\N	Accessed static asset: mobile/reserve-court	127.0.0.1	2025-05-18 12:37:10.900355
12766	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:37:19.465282
12788	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:37:40.137573
12809	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:37:42.086968
12829	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	127.0.0.1	2025-05-18 12:38:35.502701
12849	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 12:38:51.844249
12872	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:38:58.577982
12892	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 12:42:09.486489
12893	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:42:09.486423
12913	rossfreedman@gmail.com	static_asset	com.chrome.devtools	\N	Accessed static asset: .well-known/appspecific/com.chrome.devtools.json	127.0.0.1	2025-05-18 12:42:38.222908
12934	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 12:44:23.125475
12954	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	127.0.0.1	2025-05-18 12:44:29.859252
12976	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-05-18 12:52:30.602464
12997	rossfreedman@gmail.com	click	/mobile	a	a: Team Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 12:52:42.52284
13019	rossfreedman@gmail.com	click	/mobile/lineup-escrow	page_visit	page_visit: Lineup Escrow™ | Rally -> /mobile/lineup-escrow	127.0.0.1	2025-05-18 12:52:54.167817
13039	rossfreedman@gmail.com	click	/mobile	a	a: Improve my game -> http://127.0.0.1:8080/mobile/improve	127.0.0.1	2025-05-18 12:58:27.318497
13061	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:59:48.86054
13081	rossfreedman@gmail.com	click	/mobile/view-schedule	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 13:02:04.492337
13101	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:07:40.265954
13122	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:07:44.606612
13143	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:09:57.375261
13163	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:15:49.504452
13183	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:19:44.322628
13203	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:26:38.476895
13225	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:30:56.603684
13245	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:33:54.866689
13265	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:34:01.100006
13286	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:35:14.576496
13306	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:35:27.03555
13327	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:36:44.472756
13346	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:38:00.842612
13366	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:38:29.591017
13388	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:38:52.174092
13407	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:39:18.9539
13429	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:47:14.711769
13449	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/15/2024, Available: True	127.0.0.1	2025-05-18 13:47:50.327688
13469	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:48:08.120063
13491	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:48:28.037342
13490	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:48:28.037377
13512	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:50:49.82386
13533	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:50:57.154024
13553	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:51:04.801565
13575	rossfreedman@gmail.com	click	/mobile/ask-ai	page_visit	page_visit: Rally -> /mobile/ask-ai	127.0.0.1	2025-05-18 13:52:20.207292
13595	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 13:54:27.912659
13615	rossfreedman@gmail.com	click	/mobile/availability	button	button: 	127.0.0.1	2025-05-18 13:55:05.703466
13635	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:56:20.573694
13656	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:58:53.052745
13677	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:01:31.180625
13697	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 14:03:45.171213
13751	rossfreedman@gmail.com	auth	\N	logout	\N	127.0.0.1	2025-05-18 14:06:18.807404
12602	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:29:03.799497
12622	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:30:28.158496
12642	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:33:56.307851
12664	rossfreedman@gmail.com	static_asset	com.chrome.devtools	\N	Accessed static asset: .well-known/appspecific/com.chrome.devtools.json	127.0.0.1	2025-05-18 12:35:21.979048
12684	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:18.890072
12706	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:33.670734
12705	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:33.670564
12726	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:37:00.118651
12747	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:10.90113
12767	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:19.520789
12789	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 12:37:40.144091
12810	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 12:37:42.086948
12831	rossfreedman@gmail.com	click	/mobile/my-series	page_visit	page_visit: Rally -> /mobile/my-series	127.0.0.1	2025-05-18 12:38:35.594199
12850	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:38:51.855695
12873	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:38:59.175512
12894	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:42:09.498152
12914	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:44:20.66712
12935	rossfreedman@gmail.com	static_asset	favicon	\N	Accessed static asset: favicon.ico	127.0.0.1	2025-05-18 12:44:23.156131
12955	rossfreedman@gmail.com	click	/mobile/my-series	page_visit	page_visit: Rally -> /mobile/my-series	127.0.0.1	2025-05-18 12:44:29.937565
12977	rossfreedman@gmail.com	click	/mobile/analyze-me	page_visit	page_visit: Rally -> /mobile/analyze-me	127.0.0.1	2025-05-18 12:52:30.701683
12998	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:52:42.522876
13020	rossfreedman@gmail.com	click	/mobile/lineup-escrow	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:52:54.965805
13041	rossfreedman@gmail.com	click	/mobile/improve	page_visit	page_visit: Rally -> /mobile/improve	127.0.0.1	2025-05-18 12:58:27.389022
13062	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:59:48.860577
13082	rossfreedman@gmail.com	click	/mobile	a	a: Team Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 13:02:05.800516
13102	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:07:40.270593
13123	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:09:41.325561
13144	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:09:57.379998
13164	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:15:50.300318
13185	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:21:14.436939
13204	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:26:38.481988
13226	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:30:57.298545
13246	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: False	127.0.0.1	2025-05-18 13:33:54.874805
13266	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:34:01.904759
13287	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:35:14.580211
13307	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:35:27.038169
13326	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:36:44.472717
13347	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:38:21.680423
13348	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:38:21.680373
13368	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:38:29.594794
13389	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/08/2024, Available: False	127.0.0.1	2025-05-18 13:38:52.183973
13409	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:39:19.022853
13431	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:47:41.138146
13450	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:47:53.837305
13470	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/22/2024, Available: True	127.0.0.1	2025-05-18 13:48:08.121481
13492	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:48:28.042628
13513	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:50:49.829685
13534	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:50:57.155188
13554	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:51:04.805906
13576	rossfreedman@gmail.com	click	/mobile/ask-ai	page_visit	page_visit: Rally -> /mobile/ask-ai	127.0.0.1	2025-05-18 13:52:20.209904
13596	rossfreedman@gmail.com	click	/mobile	button	button: 	127.0.0.1	2025-05-18 13:54:30.654124
13616	rossfreedman@gmail.com	auth	\N	logout	\N	127.0.0.1	2025-05-18 13:55:07.662836
13636	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:56:22.206713
13657	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:58:54.690287
13678	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:01:31.182513
13699	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 14:03:45.267383
13698	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 14:03:45.26741
13719	rossfreedman@gmail.com	click	/mobile	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 14:05:01.314428
12604	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:29:05.960548
12623	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:31:32.67306
12643	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:33:56.364945
12665	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:36:12.127488
12685	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:36:19.638717
12707	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:33.674122
12727	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:37:00.133506
12748	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:37:10.90117
12768	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-05-18 12:37:19.54546
12790	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:37:40.144725
12811	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:37:42.094069
12830	rossfreedman@gmail.com	click	/mobile/my-series	page_visit	page_visit: Rally -> /mobile/my-series	127.0.0.1	2025-05-18 12:38:35.594164
12851	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:38:51.911754
12852	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:38:51.911696
12874	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 12:38:59.199392
12895	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:42:09.553337
12915	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:44:21.045779
12936	rossfreedman@gmail.com	click	/mobile	a	a: Me -> http://127.0.0.1:8080/mobile/analyze-me	127.0.0.1	2025-05-18 12:44:24.745869
12956	rossfreedman@gmail.com	click	/mobile/my-series	page_visit	page_visit: Rally -> /mobile/my-series	127.0.0.1	2025-05-18 12:44:29.937599
12978	rossfreedman@gmail.com	click	/mobile/analyze-me	page_visit	page_visit: Rally -> /mobile/analyze-me	127.0.0.1	2025-05-18 12:52:30.70136
12999	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:52:42.548172
13021	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:57:05.518276
13040	rossfreedman@gmail.com	click	/mobile/improve	page_visit	page_visit: Rally -> /mobile/improve	127.0.0.1	2025-05-18 12:58:27.388968
13063	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:59:48.863024
13083	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 13:02:05.805331
13103	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:07:40.338146
13124	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:09:41.325516
13145	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:10:01.095575
13165	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:15:50.304318
13184	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:21:14.436535
13205	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:27:42.425199
13227	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:30:57.306988
13247	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:33:55.455046
13267	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/01/2024, Available: True	127.0.0.1	2025-05-18 13:34:01.913976
13288	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:35:15.3576
13308	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:35:28.100293
13328	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:36:44.477393
13350	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:38:21.755744
13369	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:38:31.845918
13390	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:38:52.756418
13410	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:39:19.023349
13430	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:47:41.138135
13451	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/08/2024, Available: True	127.0.0.1	2025-05-18 13:47:53.846958
13471	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:48:09.586268
13493	rossfreedman@gmail.com	click	/mobile	button	button: 	127.0.0.1	2025-05-18 13:48:29.780117
13514	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 13:50:50.619821
13535	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 13:50:57.822128
13555	rossfreedman@gmail.com	click	/mobile	button	button: 	127.0.0.1	2025-05-18 13:51:09.357153
13577	rossfreedman@gmail.com	click	/mobile/ask-ai	button	button: 	127.0.0.1	2025-05-18 13:52:20.817899
13597	rossfreedman@gmail.com	auth	\N	logout	\N	127.0.0.1	2025-05-18 13:54:32.071008
13617	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 13:55:07.663911
13638	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:56:22.374642
13658	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:58:54.701161
13679	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:01:31.55861
13700	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 14:03:45.270105
13720	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:05:01.380836
13734	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:06:14.337282
13744	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:06:14.908569
13754	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:06:18.871735
12603	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	Accessed Ask AI page	127.0.0.1	2025-05-18 12:29:05.960547
12624	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:31:32.742604
12645	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:33:57.065946
12644	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:33:57.065956
12666	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:12.127494
12686	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:19.649299
12708	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:34.439343
12728	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:00.190454
12749	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:37:12.906131
12770	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:19.619947
12791	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:37:40.166289
12812	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:37:42.106546
12832	rossfreedman@gmail.com	click	/mobile/my-series	page_visit	page_visit: Rally -> /mobile/my-series	127.0.0.1	2025-05-18 12:38:35.596444
12853	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:38:51.914879
12875	rossfreedman@gmail.com	static_asset	favicon	\N	Accessed static asset: favicon.ico	127.0.0.1	2025-05-18 12:38:59.224306
12896	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:42:09.553434
12916	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:44:21.045753
12937	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-05-18 12:44:24.773176
12957	rossfreedman@gmail.com	click	/mobile/my-series	page_visit	page_visit: Rally -> /mobile/my-series	127.0.0.1	2025-05-18 12:44:29.937882
12979	rossfreedman@gmail.com	click	/mobile/analyze-me	page_visit	page_visit: Rally -> /mobile/analyze-me	127.0.0.1	2025-05-18 12:52:30.703504
13001	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:52:42.605904
13023	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:57:05.590338
13042	rossfreedman@gmail.com	click	/mobile/improve	page_visit	page_visit: Rally -> /mobile/improve	127.0.0.1	2025-05-18 12:58:27.391731
13064	rossfreedman@gmail.com	click	/mobile	a	a: Me -> http://127.0.0.1:8080/mobile/analyze-me	127.0.0.1	2025-05-18 13:01:57.678886
13084	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:02:05.872641
13104	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:07:40.338604
13125	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:09:41.33051
13146	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:12:03.831171
13167	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:16:59.453966
13186	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:21:14.440501
13206	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:27:42.425169
13228	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:32:26.782411
13248	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/01/2024, Available: True	127.0.0.1	2025-05-18 13:33:55.466592
13268	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/01/2024, Available: False	127.0.0.1	2025-05-18 13:34:03.96889
13289	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: False	127.0.0.1	2025-05-18 13:35:15.366329
13309	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:35:28.266742
13329	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:37:52.766998
13349	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:38:21.755552
13370	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: False	127.0.0.1	2025-05-18 13:38:31.855943
13391	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/15/2024, Available: False	127.0.0.1	2025-05-18 13:38:52.765522
13411	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:39:19.026976
13432	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:47:41.142564
13452	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:47:55.22344
13472	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/29/2024, Available: True	127.0.0.1	2025-05-18 13:48:09.595309
13494	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 13:48:31.522893
13495	rossfreedman@gmail.com	auth	\N	logout	\N	127.0.0.1	2025-05-18 13:48:31.522167
13515	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 13:50:50.624022
13536	rossfreedman@gmail.com	click	/mobile	a	a: My Series -> http://127.0.0.1:8080/mobile/myseries	127.0.0.1	2025-05-18 13:50:58.494442
13557	rossfreedman@gmail.com	auth	\N	logout	\N	127.0.0.1	2025-05-18 13:51:12.846477
13556	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 13:51:12.84646
13578	rossfreedman@gmail.com	click	/mobile/ask-ai	a	a: Logout -> http://127.0.0.1:8080/mobile/ask-ai#	127.0.0.1	2025-05-18 13:52:22.148581
13598	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 13:54:32.071043
13618	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:55:07.66459
13637	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:56:22.374615
13659	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 13:58:56.018503
13680	rossfreedman@gmail.com	click	/mobile	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 14:01:31.560821
13701	rossfreedman@gmail.com	click	/mobile/view-schedule	button	button: 	127.0.0.1	2025-05-18 14:03:46.963049
13721	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:05:01.380804
13735	rossfreedman@gmail.com	click	/mobile	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 14:06:14.601357
12605	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:29:06.035713
12625	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:31:33.686719
12646	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:33:57.075756
12667	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-05-18 12:36:12.151226
12687	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:20.822543
12709	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:36:35.084427
12729	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:00.190439
12750	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:12.908121
12769	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:19.619974
12793	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:37:40.223105
12813	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:37:42.163716
12833	rossfreedman@gmail.com	click	/mobile/my-series	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:38:36.607015
12855	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	Accessed Ask AI page	127.0.0.1	2025-05-18 12:38:53.359812
12856	rossfreedman@gmail.com	click	/mobile	a	a: Ask Rally AI -> http://127.0.0.1:8080/mobile/ask-ai	127.0.0.1	2025-05-18 12:38:53.359828
12876	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:42:07.439463
12897	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:42:09.556627
12917	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:44:21.050541
12938	rossfreedman@gmail.com	click	/mobile/analyze-me	page_visit	page_visit: Rally -> /mobile/analyze-me	127.0.0.1	2025-05-18 12:44:24.865119
12958	rossfreedman@gmail.com	click	/mobile/my-series	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:44:31.075816
12980	rossfreedman@gmail.com	click	/mobile/analyze-me	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:52:31.449879
13000	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:52:42.605835
13022	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:57:05.590151
13043	rossfreedman@gmail.com	click	/mobile/improve	button	button: 	127.0.0.1	2025-05-18 12:58:29.115167
13065	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-05-18 13:01:57.705963
13085	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:02:05.87271
13105	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:07:40.34044
13126	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:09:43.079448
13147	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:12:03.83157
13166	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:16:59.453936
13187	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:21:16.080419
13207	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:27:42.4298
13229	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:32:26.782428
13249	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:33:57.182617
13269	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:34:03.974318
13290	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:35:19.209433
13310	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:35:28.266896
13330	rossfreedman@gmail.com	click	/mobile/view-schedule	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:37:52.767624
13351	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:38:21.759048
13371	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:38:32.45554
13392	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:38:53.47317
13412	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:39:19.843752
13433	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:47:42.055401
13453	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/29/2024, Available: True	127.0.0.1	2025-05-18 13:47:55.232566
13473	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:48:13.08776
13496	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:48:31.52426
13516	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:50:50.710115
13517	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:50:50.710156
13537	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	127.0.0.1	2025-05-18 13:50:58.496514
13558	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:51:12.850449
13579	rossfreedman@gmail.com	auth	\N	logout	\N	127.0.0.1	2025-05-18 13:52:22.148537
13599	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:54:32.072297
13619	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:55:07.729682
13639	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:56:22.379783
13660	rossfreedman@gmail.com	click	/mobile	a	a: My Club -> http://127.0.0.1:8080/mobile/my-club	127.0.0.1	2025-05-18 13:58:57.350838
13681	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:01:31.620563
13702	rossfreedman@gmail.com	click	/mobile/view-schedule	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 14:03:48.362503
13722	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:05:01.383731
13736	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:06:14.601301
13745	rossfreedman@gmail.com	click	/mobile	a	a: My Team -> http://127.0.0.1:8080/mobile/myteam	127.0.0.1	2025-05-18 14:06:16.219141
13753	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:06:18.870961
12606	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:29:07.907427
12626	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:31:33.750548
12647	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:33:57.091231
12668	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:12.272727
12688	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:36:21.663289
12710	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:35.090611
12730	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:00.19525
12751	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:14.492594
12771	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:19.624122
12792	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:37:40.222935
12814	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:37:42.163639
12834	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:38:37.289584
12854	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:38:53.359764
12877	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:42:07.760857
12898	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:42:10.23122
12918	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:44:21.333429
12939	rossfreedman@gmail.com	click	/mobile/analyze-me	page_visit	page_visit: Rally -> /mobile/analyze-me	127.0.0.1	2025-05-18 12:44:24.865071
12959	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:52:13.592935
12981	rossfreedman@gmail.com	click	/mobile	a	a: My Team -> http://127.0.0.1:8080/mobile/myteam	127.0.0.1	2025-05-18 12:52:32.242094
13002	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:52:42.609216
13024	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:57:05.59338
13044	rossfreedman@gmail.com	click	/mobile/improve	button	button: 	127.0.0.1	2025-05-18 12:58:31.073177
13066	rossfreedman@gmail.com	click	/mobile/analyze-me	page_visit	page_visit: Rally -> /mobile/analyze-me	127.0.0.1	2025-05-18 13:01:57.79586
13086	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:02:05.875532
13106	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:07:40.89016
13107	rossfreedman@gmail.com	click	/mobile	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:07:40.890184
13127	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:09:45.746165
13148	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:12:03.83555
13168	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:16:59.459062
13188	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:21:16.084622
13208	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:27:43.446795
13230	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:32:26.785934
13250	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:33:57.183958
13270	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:34:05.690194
13291	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/08/2024, Available: False	127.0.0.1	2025-05-18 13:35:19.218592
13311	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:35:28.270779
13331	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:37:52.83993
13352	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:38:22.635794
13372	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/01/2024, Available: False	127.0.0.1	2025-05-18 13:38:32.465081
13393	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/22/2024, Available: False	127.0.0.1	2025-05-18 13:38:53.48002
13414	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:39:20.018371
13434	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:47:42.059194
13454	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:47:55.608472
13474	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 11/12/2024, Available: True	127.0.0.1	2025-05-18 13:48:13.097195
13497	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:48:31.580091
13518	rossfreedman@gmail.com	click	/mobile/view-schedule	page_visit	page_visit: Rally -> /mobile/view-schedule	127.0.0.1	2025-05-18 13:50:50.712666
13538	rossfreedman@gmail.com	click	/mobile/my-series	page_visit	page_visit: Rally -> /mobile/my-series	127.0.0.1	2025-05-18 13:50:58.563667
13559	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:51:12.904984
13580	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:52:22.153139
13601	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:54:32.138435
13620	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:55:07.730163
13640	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:56:23.867523
13661	rossfreedman@gmail.com	click	/mobile/my-club	button	button: 	127.0.0.1	2025-05-18 13:58:58.661555
13682	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:01:31.620599
13703	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 14:03:48.536478
13723	rossfreedman@gmail.com	click	/mobile	button	button: 	127.0.0.1	2025-05-18 14:05:03.0722
13738	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:06:14.672608
13746	rossfreedman@gmail.com	click	/mobile/myteam	page_visit	page_visit: Rally -> /mobile/myteam	127.0.0.1	2025-05-18 14:06:16.295912
13755	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:06:18.874358
12607	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:29:08.68189
12627	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:31:35.633824
12648	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:33:57.152833
12669	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:12.272695
12689	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:21.672729
12711	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	127.0.0.1	2025-05-18 12:36:35.090666
12731	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:02.210794
12753	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:37:15.379818
12772	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:37:23.547741
12794	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:37:40.225377
12815	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:37:42.16701
12835	rossfreedman@gmail.com	click	/mobile	a	a: Me -> http://127.0.0.1:8080/mobile/analyze-me	127.0.0.1	2025-05-18 12:38:37.34749
12858	rossfreedman@gmail.com	click	/mobile/ask-ai	page_visit	page_visit: Rally -> /mobile/ask-ai	127.0.0.1	2025-05-18 12:38:53.422675
12878	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:42:07.760866
12899	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 12:42:10.241893
12920	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:44:21.464129
12940	rossfreedman@gmail.com	click	/mobile/analyze-me	page_visit	page_visit: Rally -> /mobile/analyze-me	127.0.0.1	2025-05-18 12:44:24.8694
12960	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:52:13.734226
12983	rossfreedman@gmail.com	click	/mobile/myteam	page_visit	page_visit: Rally -> /mobile/myteam	127.0.0.1	2025-05-18 12:52:32.320456
12982	rossfreedman@gmail.com	click	/mobile/myteam	page_visit	page_visit: Rally -> /mobile/myteam	127.0.0.1	2025-05-18 12:52:32.320437
13004	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	127.0.0.1	2025-05-18 12:52:49.196646
13003	rossfreedman@gmail.com	click	/mobile	a	a: Find Sub -> http://127.0.0.1:8080/mobile/find-subs	127.0.0.1	2025-05-18 12:52:49.196665
13025	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 12:57:06.499519
13045	rossfreedman@gmail.com	click	/mobile/improve	a	a: Improve my game -> http://127.0.0.1:8080/mobile/improve	127.0.0.1	2025-05-18 12:58:32.84764
13067	rossfreedman@gmail.com	click	/mobile/analyze-me	page_visit	page_visit: Rally -> /mobile/analyze-me	127.0.0.1	2025-05-18 13:01:57.79584
13087	rossfreedman@gmail.com	click	/mobile/view-schedule	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 13:02:06.84241
13108	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:07:40.972528
13128	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:09:47.348229
13149	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 13:12:04.784783
13169	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:17:00.083628
13189	rossfreedman@gmail.com	static_asset	com.chrome.devtools	\N	Accessed static asset: .well-known/appspecific/com.chrome.devtools.json	127.0.0.1	2025-05-18 13:21:45.77738
13209	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:27:43.453903
13232	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:32:27.492879
13251	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:33:57.253622
13271	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:34:05.690229
13292	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:35:20.864802
13312	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:35:38.053425
13332	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:37:52.841862
13353	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:38:22.810768
13374	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:38:33.549328
13373	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:38:33.549365
13394	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:38:59.345936
13413	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:39:20.018348
13435	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: False	127.0.0.1	2025-05-18 13:47:42.87831
13455	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/29/2024, Available: False	127.0.0.1	2025-05-18 13:47:55.617176
13475	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:48:13.514846
13499	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:48:31.582683
13519	rossfreedman@gmail.com	click	/mobile/view-schedule	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 13:50:51.762378
13539	rossfreedman@gmail.com	click	/mobile/my-series	page_visit	page_visit: Rally -> /mobile/my-series	127.0.0.1	2025-05-18 13:50:58.564449
13560	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:51:12.904944
13581	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:52:22.21409
13600	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:54:32.138441
13621	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:55:07.730894
13641	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 10/01/2024, Available: False	127.0.0.1	2025-05-18 13:56:23.87573
13662	rossfreedman@gmail.com	auth	\N	logout	\N	127.0.0.1	2025-05-18 13:59:00.253815
13683	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:01:31.624158
13704	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 14:03:48.536452
13724	rossfreedman@gmail.com	auth	\N	logout	\N	127.0.0.1	2025-05-18 14:05:05.442021
12608	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-05-18 12:29:08.707601
12628	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 12:31:35.658642
12649	rossfreedman@gmail.com	static_asset	com.chrome.devtools	\N	Accessed static asset: .well-known/appspecific/com.chrome.devtools.json	127.0.0.1	2025-05-18 12:34:18.692969
12670	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:12.277831
12690	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:36:26.08541
12712	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:36:35.150172
12734	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:37:05.26638
12732	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	127.0.0.1	2025-05-18 12:37:05.266323
12752	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:15.379823
12773	rossfreedman@gmail.com	click	\N	click	Clicked button	127.0.0.1	2025-05-18 12:37:23.550561
12795	rossfreedman@gmail.com	api_access	\N	api_log-activity	Method: POST	127.0.0.1	2025-05-18 12:37:40.736182
12816	rossfreedman@gmail.com	static_asset	com.chrome.devtools	\N	Accessed static asset: .well-known/appspecific/com.chrome.devtools.json	127.0.0.1	2025-05-18 12:37:49.123144
12836	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	127.0.0.1	2025-05-18 12:38:37.376438
12857	rossfreedman@gmail.com	click	/mobile/ask-ai	page_visit	page_visit: Rally -> /mobile/ask-ai	127.0.0.1	2025-05-18 12:38:53.422661
12879	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:42:07.76351
12900	rossfreedman@gmail.com	static_asset	favicon	\N	Accessed static asset: favicon.ico	127.0.0.1	2025-05-18 12:42:10.262936
12919	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:44:21.464252
12941	rossfreedman@gmail.com	click	/mobile/analyze-me	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 12:44:25.622286
12961	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 12:52:13.734321
12984	rossfreedman@gmail.com	click	/mobile/myteam	page_visit	page_visit: Rally -> /mobile/myteam	127.0.0.1	2025-05-18 12:52:32.324184
13005	rossfreedman@gmail.com	click	/mobile/find-subs	page_visit	page_visit: Rally -> /mobile/find-subs	127.0.0.1	2025-05-18 12:52:49.269129
13026	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 12:57:06.506315
13046	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	127.0.0.1	2025-05-18 12:58:32.848918
13068	rossfreedman@gmail.com	click	/mobile/analyze-me	page_visit	page_visit: Rally -> /mobile/analyze-me	127.0.0.1	2025-05-18 13:01:57.802787
13088	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:02:08.89823
13109	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:07:40.972455
13129	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:09:48.90134
13150	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 13:12:04.791837
13170	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:17:00.083589
13191	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:22:24.422047
13211	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:28:53.942566
13231	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:32:27.492799
13252	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:33:57.253642
13272	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:34:05.694321
13293	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 13:35:20.864746
13313	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: False	127.0.0.1	2025-05-18 13:35:38.061468
13333	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:37:52.843035
13354	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:38:22.810746
13376	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:38:33.622376
13395	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 12/10/2024, Available: True	127.0.0.1	2025-05-18 13:38:59.354726
13415	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 13:39:20.022587
13436	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 13:47:42.882448
13456	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 13:47:56.969265
13476	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 11/12/2024, Available: False	127.0.0.1	2025-05-18 13:48:13.52401
13498	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:48:31.582491
13520	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:50:52.243123
13540	rossfreedman@gmail.com	click	/mobile/my-series	page_visit	page_visit: Rally -> /mobile/my-series	127.0.0.1	2025-05-18 13:50:58.565991
13561	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:51:12.908453
13582	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:52:22.214112
13602	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 13:54:32.141577
13622	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 13:55:09.168107
13642	rossfreedman@gmail.com	click	/mobile/availability	button	button: 	127.0.0.1	2025-05-18 13:56:25.147879
13663	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 13:59:00.256535
13684	rossfreedman@gmail.com	click	/mobile	button	button: 	127.0.0.1	2025-05-18 14:01:33.579835
13705	rossfreedman@gmail.com	click	/mobile/availability	page_visit	page_visit: Update Availability | Rally -> /mobile/availability	127.0.0.1	2025-05-18 14:03:48.541961
13725	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 14:05:05.441901
13737	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:06:14.672595
13747	rossfreedman@gmail.com	click	/mobile/myteam	page_visit	page_visit: Rally -> /mobile/myteam	127.0.0.1	2025-05-18 14:06:16.29596
12587	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	Accessed Ask AI page	127.0.0.1	2025-05-18 12:27:03.587818
13758	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:08:18.381863
13761	rossfreedman@gmail.com	click	/mobile	a	a:  -> http://127.0.0.1:8080/mobile	127.0.0.1	2025-05-18 14:08:19.061109
13764	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:08:19.134368
13767	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 14:08:21.612421
13770	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:08:21.669846
13773	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:12:09.021675
13776	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:12:09.098474
13780	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:12:09.660134
13783	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 14:12:12.884174
13785	rossfreedman@gmail.com	auth	\N	login	Successful login	127.0.0.1	2025-05-18 16:44:34.80656
13788	rossfreedman@gmail.com	click	/mobile	a	a: View Schedule -> http://127.0.0.1:8080/mobile/view-schedule	127.0.0.1	2025-05-18 16:44:36.012018
13792	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 16:44:41.252784
13796	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: False	127.0.0.1	2025-05-18 16:44:42.641944
13801	rossfreedman@gmail.com	click	/mobile/availability	button	button: 	127.0.0.1	2025-05-18 16:44:45.861513
13800	rossfreedman@gmail.com	click	/mobile/availability	button	button: 	127.0.0.1	2025-05-18 16:44:45.861549
13804	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 16:44:48.3206
13808	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 16:44:49.648371
13809	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 16:44:49.648428
13812	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 16:44:50.004617
13813	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 16:44:50.00468
13817	rossfreedman@gmail.com	click	/mobile/availability	button	button: 	127.0.0.1	2025-05-18 16:46:27.039406
13816	rossfreedman@gmail.com	click	/mobile/availability	button	button: 	127.0.0.1	2025-05-18 16:46:27.039367
13820	rossfreedman@gmail.com	click	/mobile/availability	a	a: Improve my game -> http://127.0.0.1:8080/mobile/improve	127.0.0.1	2025-05-18 16:46:28.260893
13823	rossfreedman@gmail.com	click	/mobile/improve	a	a: Logout -> http://127.0.0.1:8080/mobile/improve#	127.0.0.1	2025-05-18 16:46:40.126554
13826	rossfreedman@gmail.com	click	/mobile/improve	a	a: Logout -> http://127.0.0.1:8080/mobile/improve#	127.0.0.1	2025-05-18 16:46:41.257627
13829	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	127.0.0.1	2025-05-18 16:48:09.154326
13832	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	127.0.0.1	2025-05-18 16:48:12.639202
13835	rossfreedman@gmail.com	click	/mobile/improve	button	button: 	127.0.0.1	2025-05-18 16:48:13.565947
13838	rossfreedman@gmail.com	click	/mobile/improve	a	a: My Club -> http://127.0.0.1:8080/mobile/my-club	127.0.0.1	2025-05-18 16:48:14.670714
13842	rossfreedman@gmail.com	click	/mobile/my-club	a	a: Logout -> http://127.0.0.1:8080/mobile/my-club#	127.0.0.1	2025-05-18 16:48:21.995823
13847	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 17:04:41.770104
13849	rossfreedman@gmail.com	click	/mobile/availability	button	button: Sorry, can't	127.0.0.1	2025-05-18 17:04:43.10382
13852	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 17:04:43.526627
13855	rossfreedman@gmail.com	click	/mobile/availability	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 17:04:44.735447
13859	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:04:50.257914
13858	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:04:50.257961
13862	rossfreedman@gmail.com	click	/mobile	a	a: Lineup Escrow -> http://127.0.0.1:8080/mobile/lineup-escrow	127.0.0.1	2025-05-18 17:04:52.284779
13865	rossfreedman@gmail.com	click	/mobile/lineup-escrow	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 17:04:54.261598
13868	rossfreedman@gmail.com	click	/mobile	button	button: 	127.0.0.1	2025-05-18 17:06:22.134459
13872	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 17:07:02.525465
13875	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 17:07:04.120894
13880	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 17:07:08.007144
13882	rossfreedman@gmail.com	click	/mobile/availability	button	button: 	127.0.0.1	2025-05-18 17:08:15.611738
13886	rossfreedman@gmail.com	click	/mobile/availability	button	button: 	127.0.0.1	2025-05-18 17:14:23.339606
13887	rossfreedman@gmail.com	click	/mobile/availability	button	button: 	127.0.0.1	2025-05-18 17:14:23.339592
13889	rossfreedman@gmail.com	click	/mobile	button	button: 	127.0.0.1	2025-05-18 17:26:06.571222
13895	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:26:10.821107
13896	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:26:10.821048
13902	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:26:11.413077
13901	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:26:11.413139
13905	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:26:11.771097
13908	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 17:27:18.766135
13756	rossfreedman@gmail.com	static_asset	com.chrome.devtools	\N	Accessed static asset: .well-known/appspecific/com.chrome.devtools.json	127.0.0.1	2025-05-18 14:06:27.408633
13759	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:08:18.383613
13762	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:08:19.062256
13765	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:08:19.138014
13768	rossfreedman@gmail.com	auth	\N	logout	\N	127.0.0.1	2025-05-18 14:08:21.612909
13771	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:08:21.671068
13774	rossfreedman@gmail.com	click	/mobile	page_visit	page_visit: Rally -> /mobile	127.0.0.1	2025-05-18 14:12:09.09529
13777	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 14:12:09.579516
13781	rossfreedman@gmail.com	click	/mobile	button	button: 	127.0.0.1	2025-05-18 14:12:11.248552
13786	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 16:44:34.822244
13789	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	127.0.0.1	2025-05-18 16:44:36.014907
13793	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 16:44:41.257924
13797	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 16:44:43.078269
13798	rossfreedman@gmail.com	click	/mobile/availability	button	button: I can play	127.0.0.1	2025-05-18 16:44:43.078138
13802	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 16:44:47.491394
13805	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 16:44:48.320547
13810	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 16:44:49.822903
13814	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 16:44:50.285902
13818	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	127.0.0.1	2025-05-18 16:46:28.260339
13822	rossfreedman@gmail.com	click	/mobile/improve	button	button: 	127.0.0.1	2025-05-18 16:46:29.093587
13824	rossfreedman@gmail.com	click	/mobile/improve	a	a: Logout -> http://127.0.0.1:8080/mobile/improve#	127.0.0.1	2025-05-18 16:46:40.131803
13827	rossfreedman@gmail.com	click	/mobile/improve	a	a: Logout -> http://127.0.0.1:8080/mobile/improve#	127.0.0.1	2025-05-18 16:47:10.037895
13831	rossfreedman@gmail.com	click	/mobile/improve	button	button: 	127.0.0.1	2025-05-18 16:48:11.333296
13833	rossfreedman@gmail.com	click	/mobile/improve	a	a: Improve my game -> http://127.0.0.1:8080/mobile/improve	127.0.0.1	2025-05-18 16:48:12.644126
13836	rossfreedman@gmail.com	click	/mobile/improve	button	button: 	127.0.0.1	2025-05-18 16:48:13.565984
13840	rossfreedman@gmail.com	click	/mobile/my-club	button	button: 	127.0.0.1	2025-05-18 16:48:16.853777
13839	rossfreedman@gmail.com	click	/mobile/my-club	button	button: 	127.0.0.1	2025-05-18 16:48:16.853737
13843	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 17:04:40.498065
13846	rossfreedman@gmail.com	click	/mobile	a	a: Manage Availability -> http://127.0.0.1:8080/mobile/availability	127.0.0.1	2025-05-18 17:04:41.768768
13850	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: False	127.0.0.1	2025-05-18 17:04:43.113647
13853	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 09/24/2024, Available: True	127.0.0.1	2025-05-18 17:04:43.533393
13856	rossfreedman@gmail.com	click	/mobile	button	button: 	127.0.0.1	2025-05-18 17:04:48.569951
13861	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:04:51.469424
13863	rossfreedman@gmail.com	page_visit	mobile_lineup_escrow	\N	Accessed mobile lineup escrow page	127.0.0.1	2025-05-18 17:04:52.286736
13866	rossfreedman@gmail.com	click	/mobile/lineup-escrow	a	a:  -> javascript:history.back()	127.0.0.1	2025-05-18 17:04:54.263119
13869	rossfreedman@gmail.com	click	/mobile	button	button: 	127.0.0.1	2025-05-18 17:06:22.137643
13873	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 17:07:03.27973
13876	rossfreedman@gmail.com	click	/mobile/availability	button	button: 	127.0.0.1	2025-05-18 17:07:04.945739
13877	rossfreedman@gmail.com	click	/mobile/availability	button	button: 	127.0.0.1	2025-05-18 17:07:04.94569
13881	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 17:07:08.009634
13884	rossfreedman@gmail.com	click	/mobile/availability	a	a: Logout -> http://127.0.0.1:8080/mobile/availability#	127.0.0.1	2025-05-18 17:08:18.202382
13888	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	127.0.0.1	2025-05-18 17:26:04.116903
13892	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:26:09.044406
13891	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:26:09.044359
13897	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:26:11.032009
13898	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:26:11.031944
13904	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:26:11.593025
13906	rossfreedman@gmail.com	click	/mobile	a	a: Logout -> http://127.0.0.1:8080/mobile#	127.0.0.1	2025-05-18 17:26:11.77131
\.


--
-- Data for Name: user_instructions; Type: TABLE DATA; Schema: public; Owner: rossfreedman
--

COPY public.user_instructions (id, user_email, instruction, series_id, team_id, created_at, series_name, is_active, team_name) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: rossfreedman
--

COPY public.users (id, email, password_hash, first_name, last_name, club_id, series_id, club_automation_password, created_at, last_login) FROM stdin;
8	jessfreedman@gmail.com	pbkdf2:sha256:1000000$30H2lfQJefbpXSQ9$bc29fb0d6b2605362513fd9aefedfe4dc77a591de9d478a8d5f8794c20912d27	Jess	Freedman	1	19	\N	2025-05-18 19:42:01.24637	\N
9	aseyb@aol.com	pbkdf2:sha256:1000000$bveYOeds3wJgJq9G$6bdd560cca5c75857bd6fc7c53e9692c6bede9c150d21109423e7ccfe3ac93c2	Adam	Seyb	1	22	\N	2025-05-18 20:29:50.860784	\N
7	rossfreedman@gmail.com	pbkdf2:sha256:1000000$fsxkBUxUvatei6gz$322d074c5e8035fb7688a0a53cbc0a6aeba587a3ad9eb066b70372d29554166c	Ross	Freedman	1	22	\N	2025-05-18 11:31:24.509828	2025-05-19 11:39:00.179584
\.


--
-- Name: clubs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rossfreedman
--

SELECT pg_catalog.setval('public.clubs_id_seq', 180, true);


--
-- Name: player_availability_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rossfreedman
--

SELECT pg_catalog.setval('public.player_availability_id_seq', 227, true);


--
-- Name: series_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rossfreedman
--

SELECT pg_catalog.setval('public.series_id_seq', 180, true);


--
-- Name: user_activity_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rossfreedman
--

SELECT pg_catalog.setval('public.user_activity_logs_id_seq', 13908, true);


--
-- Name: user_instructions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rossfreedman
--

SELECT pg_catalog.setval('public.user_instructions_id_seq', 30, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rossfreedman
--

SELECT pg_catalog.setval('public.users_id_seq', 9, true);


--
-- Name: clubs clubs_name_key; Type: CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.clubs
    ADD CONSTRAINT clubs_name_key UNIQUE (name);


--
-- Name: clubs clubs_pkey; Type: CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.clubs
    ADD CONSTRAINT clubs_pkey PRIMARY KEY (id);


--
-- Name: player_availability player_availability_pkey; Type: CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.player_availability
    ADD CONSTRAINT player_availability_pkey PRIMARY KEY (id);


--
-- Name: player_availability player_availability_player_name_match_date_series_id_key; Type: CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.player_availability
    ADD CONSTRAINT player_availability_player_name_match_date_series_id_key UNIQUE (player_name, match_date, series_id);


--
-- Name: series series_name_key; Type: CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.series
    ADD CONSTRAINT series_name_key UNIQUE (name);


--
-- Name: series series_pkey; Type: CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.series
    ADD CONSTRAINT series_pkey PRIMARY KEY (id);


--
-- Name: user_activity_logs user_activity_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.user_activity_logs
    ADD CONSTRAINT user_activity_logs_pkey PRIMARY KEY (id);


--
-- Name: user_instructions user_instructions_pkey; Type: CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.user_instructions
    ADD CONSTRAINT user_instructions_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_player_availability; Type: INDEX; Schema: public; Owner: rossfreedman
--

CREATE INDEX idx_player_availability ON public.player_availability USING btree (player_name, match_date, series_id);


--
-- Name: idx_user_activity_logs_user_email; Type: INDEX; Schema: public; Owner: rossfreedman
--

CREATE INDEX idx_user_activity_logs_user_email ON public.user_activity_logs USING btree (user_email, "timestamp");


--
-- Name: idx_user_email; Type: INDEX; Schema: public; Owner: rossfreedman
--

CREATE INDEX idx_user_email ON public.users USING btree (email);


--
-- Name: idx_user_instructions_email; Type: INDEX; Schema: public; Owner: rossfreedman
--

CREATE INDEX idx_user_instructions_email ON public.user_instructions USING btree (user_email);


--
-- Name: player_availability player_availability_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.player_availability
    ADD CONSTRAINT player_availability_series_id_fkey FOREIGN KEY (series_id) REFERENCES public.series(id);


--
-- Name: users users_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id);


--
-- Name: users users_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_series_id_fkey FOREIGN KEY (series_id) REFERENCES public.series(id);


--
-- PostgreSQL database dump complete
--

