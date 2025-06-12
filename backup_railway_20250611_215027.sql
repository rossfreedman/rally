--
-- PostgreSQL database dump
--

-- Dumped from database version 16.8 (Debian 16.8-1.pgdg120+1)
-- Dumped by pg_dump version 16.9 (Homebrew)

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: club_leagues; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.club_leagues (
    id integer NOT NULL,
    club_id integer NOT NULL,
    league_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: club_leagues_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.club_leagues_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: club_leagues_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.club_leagues_id_seq OWNED BY public.club_leagues.id;


--
-- Name: clubs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clubs (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);


--
-- Name: clubs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clubs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clubs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clubs_id_seq OWNED BY public.clubs.id;


--
-- Name: leagues; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.leagues (
    id integer NOT NULL,
    league_id character varying(255) NOT NULL,
    league_name character varying(255) NOT NULL,
    league_url character varying(512),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: leagues_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.leagues_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: leagues_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.leagues_id_seq OWNED BY public.leagues.id;


--
-- Name: player_availability; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.player_availability (
    id integer NOT NULL,
    player_name character varying(255) NOT NULL,
    availability_status integer DEFAULT 3 NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    series_id integer NOT NULL,
    match_date timestamp with time zone NOT NULL,
    tenniscores_player_id character varying(50),
    CONSTRAINT match_date_must_be_midnight_utc CHECK (((date_part('hour'::text, (match_date AT TIME ZONE 'UTC'::text)) = (0)::double precision) AND (date_part('minute'::text, (match_date AT TIME ZONE 'UTC'::text)) = (0)::double precision) AND (date_part('second'::text, (match_date AT TIME ZONE 'UTC'::text)) = (0)::double precision))),
    CONSTRAINT valid_availability_status CHECK ((availability_status = ANY (ARRAY[1, 2, 3])))
);


--
-- Name: player_availability_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.player_availability_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: player_availability_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.player_availability_id_seq OWNED BY public.player_availability.id;


--
-- Name: series; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.series (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);


--
-- Name: series_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.series_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: series_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.series_id_seq OWNED BY public.series.id;


--
-- Name: series_leagues; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.series_leagues (
    id integer NOT NULL,
    series_id integer NOT NULL,
    league_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: series_leagues_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.series_leagues_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: series_leagues_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.series_leagues_id_seq OWNED BY public.series_leagues.id;


--
-- Name: user_activity_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_activity_logs (
    id integer NOT NULL,
    user_email character varying(255),
    activity_type character varying(100),
    page character varying(255),
    action character varying(255),
    details text,
    ip_address character varying(45),
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: user_activity_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_activity_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_activity_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_activity_logs_id_seq OWNED BY public.user_activity_logs.id;


--
-- Name: user_instructions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_instructions (
    id integer NOT NULL,
    user_email character varying(255) NOT NULL,
    instruction text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    team_id integer,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: user_instructions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_instructions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_instructions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_instructions_id_seq OWNED BY public.user_instructions.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255),
    first_name character varying(100),
    last_name character varying(100),
    club_id integer,
    series_id integer,
    is_admin boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    club_automation_password character varying(255),
    last_login timestamp without time zone,
    tenniscores_player_id character varying(255),
    league_id integer
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: club_leagues id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_leagues ALTER COLUMN id SET DEFAULT nextval('public.club_leagues_id_seq'::regclass);


--
-- Name: clubs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clubs ALTER COLUMN id SET DEFAULT nextval('public.clubs_id_seq'::regclass);


--
-- Name: leagues id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leagues ALTER COLUMN id SET DEFAULT nextval('public.leagues_id_seq'::regclass);


--
-- Name: player_availability id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_availability ALTER COLUMN id SET DEFAULT nextval('public.player_availability_id_seq'::regclass);


--
-- Name: series id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series ALTER COLUMN id SET DEFAULT nextval('public.series_id_seq'::regclass);


--
-- Name: series_leagues id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_leagues ALTER COLUMN id SET DEFAULT nextval('public.series_leagues_id_seq'::regclass);


--
-- Name: user_activity_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_activity_logs ALTER COLUMN id SET DEFAULT nextval('public.user_activity_logs_id_seq'::regclass);


--
-- Name: user_instructions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_instructions ALTER COLUMN id SET DEFAULT nextval('public.user_instructions_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.alembic_version (version_num) FROM stdin;
22cdc4d8bba3
\.


--
-- Data for Name: club_leagues; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.club_leagues (id, club_id, league_id, created_at) FROM stdin;
1	1	1	2025-06-07 12:13:00.055329
2	2	1	2025-06-07 12:13:00.061755
3	3	1	2025-06-07 12:13:00.064341
4	4	1	2025-06-07 12:13:00.066614
5	5	1	2025-06-07 12:13:00.077171
6	6	1	2025-06-07 12:13:00.080406
7	7	1	2025-06-07 12:13:00.083583
8	8	1	2025-06-07 12:13:00.085935
9	9	1	2025-06-07 12:13:00.088288
10	10	1	2025-06-07 12:13:00.090918
11	11	1	2025-06-07 12:13:00.093571
12	12	1	2025-06-07 12:13:00.095809
13	13	1	2025-06-07 12:13:00.09869
14	14	1	2025-06-07 12:13:00.101105
15	15	1	2025-06-07 12:13:00.103739
16	16	1	2025-06-07 12:13:00.106271
17	17	1	2025-06-07 12:13:00.108976
18	18	1	2025-06-07 12:13:00.116257
19	19	1	2025-06-07 12:13:00.119244
20	20	1	2025-06-07 12:13:00.122861
21	21	1	2025-06-07 12:13:00.125289
22	22	1	2025-06-07 12:13:00.128512
23	23	1	2025-06-07 12:13:00.132058
24	24	1	2025-06-07 12:13:00.134761
25	25	1	2025-06-07 12:13:00.137401
26	26	1	2025-06-07 12:13:00.139876
27	27	1	2025-06-07 12:13:00.142894
28	28	1	2025-06-07 12:13:00.145437
29	29	1	2025-06-07 12:13:00.147964
30	30	1	2025-06-07 12:13:00.150893
31	31	1	2025-06-07 12:13:00.153156
32	32	1	2025-06-07 12:13:00.155389
33	33	1	2025-06-07 12:13:00.166359
34	34	1	2025-06-07 12:13:00.169873
35	35	1	2025-06-07 12:13:00.173993
36	36	1	2025-06-07 12:13:00.176636
37	37	1	2025-06-07 12:13:00.178866
38	38	1	2025-06-07 12:13:00.180903
39	39	1	2025-06-07 12:13:00.183005
40	40	1	2025-06-07 12:13:00.185165
41	41	1	2025-06-07 12:13:00.188036
42	42	1	2025-06-07 12:13:00.190297
43	43	1	2025-06-07 12:13:00.193137
44	44	1	2025-06-07 12:13:00.195805
45	45	1	2025-06-07 12:13:00.197881
46	46	1	2025-06-07 12:13:00.200132
47	47	1	2025-06-07 12:13:00.205074
48	48	1	2025-06-07 12:13:00.209905
49	49	1	2025-06-07 12:13:00.212691
50	50	1	2025-06-07 12:13:00.219143
51	51	1	2025-06-07 12:13:00.224069
52	52	1	2025-06-07 12:13:00.226337
53	105	1	2025-06-07 12:13:00.229536
54	106	1	2025-06-07 12:13:00.231826
55	107	1	2025-06-07 12:13:00.234179
56	108	1	2025-06-07 12:13:00.23678
57	109	1	2025-06-07 12:13:00.238987
58	110	1	2025-06-07 12:13:00.24114
59	111	1	2025-06-07 12:13:00.243534
60	112	1	2025-06-07 12:13:00.246477
181	1	3	2025-06-07 17:36:50.525347
182	2	3	2025-06-07 17:36:50.525347
183	3	3	2025-06-07 17:36:50.525347
184	4	3	2025-06-07 17:36:50.525347
185	5	3	2025-06-07 17:36:50.525347
186	6	3	2025-06-07 17:36:50.525347
187	7	3	2025-06-07 17:36:50.525347
188	8	3	2025-06-07 17:36:50.525347
189	9	3	2025-06-07 17:36:50.525347
190	10	3	2025-06-07 17:36:50.525347
191	11	3	2025-06-07 17:36:50.525347
192	12	3	2025-06-07 17:36:50.525347
193	13	3	2025-06-07 17:36:50.525347
194	14	3	2025-06-07 17:36:50.525347
195	15	3	2025-06-07 17:36:50.525347
196	16	3	2025-06-07 17:36:50.525347
197	17	3	2025-06-07 17:36:50.525347
198	18	3	2025-06-07 17:36:50.525347
199	19	3	2025-06-07 17:36:50.525347
200	20	3	2025-06-07 17:36:50.525347
201	21	3	2025-06-07 17:36:50.525347
202	22	3	2025-06-07 17:36:50.525347
203	23	3	2025-06-07 17:36:50.525347
204	24	3	2025-06-07 17:36:50.525347
205	25	3	2025-06-07 17:36:50.525347
206	26	3	2025-06-07 17:36:50.525347
207	27	3	2025-06-07 17:36:50.525347
208	28	3	2025-06-07 17:36:50.525347
209	29	3	2025-06-07 17:36:50.525347
210	30	3	2025-06-07 17:36:50.525347
211	31	3	2025-06-07 17:36:50.525347
212	32	3	2025-06-07 17:36:50.525347
213	33	3	2025-06-07 17:36:50.525347
214	34	3	2025-06-07 17:36:50.525347
215	35	3	2025-06-07 17:36:50.525347
216	36	3	2025-06-07 17:36:50.525347
217	37	3	2025-06-07 17:36:50.525347
218	38	3	2025-06-07 17:36:50.525347
219	39	3	2025-06-07 17:36:50.525347
220	40	3	2025-06-07 17:36:50.525347
221	41	3	2025-06-07 17:36:50.525347
222	42	3	2025-06-07 17:36:50.525347
223	43	3	2025-06-07 17:36:50.525347
224	44	3	2025-06-07 17:36:50.525347
225	45	3	2025-06-07 17:36:50.525347
226	46	3	2025-06-07 17:36:50.525347
227	47	3	2025-06-07 17:36:50.525347
228	48	3	2025-06-07 17:36:50.525347
229	49	3	2025-06-07 17:36:50.525347
230	50	3	2025-06-07 17:36:50.525347
231	51	3	2025-06-07 17:36:50.525347
232	52	3	2025-06-07 17:36:50.525347
233	105	3	2025-06-07 17:36:50.525347
234	106	3	2025-06-07 17:36:50.525347
235	107	3	2025-06-07 17:36:50.525347
236	108	3	2025-06-07 17:36:50.525347
237	109	3	2025-06-07 17:36:50.525347
238	110	3	2025-06-07 17:36:50.525347
239	111	3	2025-06-07 17:36:50.525347
240	112	3	2025-06-07 17:36:50.525347
\.


--
-- Data for Name: clubs; Type: TABLE DATA; Schema: public; Owner: -
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
-- Data for Name: leagues; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.leagues (id, league_id, league_name, league_url, created_at) FROM stdin;
1	APTA_CHICAGO	APTA Chicago	https://aptachicago.tenniscores.com/	2025-06-07 12:13:00.043549
2	APTA_NATIONAL	APTA National	https://apta.tenniscores.com/	2025-06-07 12:13:00.047886
3	NSTF	North Shore Tennis Foundation	https://nstf.org/	2025-06-07 12:13:00.050428
\.


--
-- Data for Name: player_availability; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.player_availability (id, player_name, availability_status, updated_at, series_id, match_date, tenniscores_player_id) FROM stdin;
87	Ross Freedman	1	2025-06-04 08:38:02.551142	22	2025-01-04 00:00:00+00	APTA_939F9701
88	Andrew Franger	1	2025-06-04 08:39:54.72794	22	2025-02-25 00:00:00+00	APTA_DE52ECF6
89	Andrew Franger	2	2025-06-04 08:39:58.657147	22	2025-03-04 00:00:00+00	APTA_DE52ECF6
90	Andrew Franger	3	2025-06-04 08:40:01.177646	22	2025-03-01 00:00:00+00	APTA_DE52ECF6
91	Andrew Franger	1	2025-06-04 08:40:46.440414	22	2024-09-24 00:00:00+00	APTA_DE52ECF6
92	Andrew Franger	2	2025-06-04 08:40:47.542083	22	2024-10-01 00:00:00+00	APTA_DE52ECF6
93	Andrew Franger	3	2025-06-04 08:40:49.008558	22	2024-10-05 00:00:00+00	APTA_DE52ECF6
119	Ross Freedman	1	2025-06-07 15:09:48.08934	114	2025-06-19 00:00:00+00	\N
120	Ross Freedman	1	2025-06-07 15:09:49.408316	114	2025-06-23 00:00:00+00	\N
121	Ross Freedman	1	2025-06-07 15:09:50.986702	114	2025-06-26 00:00:00+00	\N
122	Ross Freedman	1	2025-06-07 15:10:12.535926	114	2025-06-30 00:00:00+00	\N
94	Ross Freedman	1	2025-06-05 21:10:11.528991	22	2025-02-25 00:00:00+00	\N
95	Ross Freedman	2	2025-06-05 21:28:06.960217	22	2025-03-04 00:00:00+00	\N
73	Ross Freedman	2	2025-06-05 23:15:44.95646	22	2025-02-11 00:00:00+00	APTA_939F9701
123	Ross Freedman	1	2025-06-07 15:10:14.785278	114	2025-07-07 00:00:00+00	\N
98	Rosss Freedman	2	2025-06-05 23:20:52.804495	22	2024-09-14 00:00:00+00	\N
99	Rosss Freedman	1	2025-06-05 23:20:55.155026	22	2024-09-21 00:00:00+00	\N
124	Ross Freedman	1	2025-06-07 15:10:17.604832	114	2025-07-10 00:00:00+00	\N
64	Ross Freedman	2	2025-06-01 19:14:25.951462	22	2024-10-19 00:00:00+00	APTA_939F9701
63	Ross Freedman	2	2025-06-01 19:15:16.292526	22	2024-10-12 00:00:00+00	APTA_939F9701
52	Ross Freedman	2	2025-06-01 19:15:19.589573	22	2024-10-22 00:00:00+00	APTA_939F9701
66	Ross Freedman	1	2025-06-01 19:15:34.245139	22	2024-10-26 00:00:00+00	APTA_939F9701
67	Ross Freedman	1	2025-06-02 07:02:53.794911	22	2025-01-07 00:00:00+00	APTA_939F9701
68	Ross Freedman	2	2025-06-02 07:03:12.823354	22	2025-01-14 00:00:00+00	APTA_939F9701
65	Ross Freedman	2	2025-06-02 07:03:17.537401	22	2025-01-11 00:00:00+00	APTA_939F9701
70	Ross Freedman	2	2025-06-02 07:04:42.080708	22	2025-02-08 00:00:00+00	APTA_939F9701
100	Rosss Freedman	2	2025-06-05 23:21:02.311352	22	2024-09-07 00:00:00+00	\N
101	Ross Freedman	1	2025-06-06 08:06:09.640477	22	2025-03-08 00:00:00+00	\N
125	Ross Freedman	1	2025-06-07 15:10:20.895868	114	2025-07-14 00:00:00+00	\N
97	Rosss Freedman	3	2025-06-06 09:37:12.096235	22	2024-10-15 00:00:00+00	\N
102	Rosss Freedman	3	2025-06-06 09:37:13.983127	22	2024-10-08 00:00:00+00	\N
103	Rosss Freedman	3	2025-06-06 09:37:29.384229	22	2025-01-21 00:00:00+00	\N
71	Ross Freedman	1	2025-06-02 16:04:38.509613	22	2025-01-28 00:00:00+00	APTA_939F9701
72	Ross Freedman	2	2025-06-02 16:04:47.359883	22	2025-02-04 00:00:00+00	APTA_939F9701
74	Ross Freedman	2	2025-06-03 20:47:16.01668	22	2025-01-21 00:00:00+00	APTA_939F9701
84	Ross Freedman	1	2025-06-03 21:00:18.921891	22	2024-12-03 00:00:00+00	APTA_939F9701
50	Ross Freedman	1	2025-06-03 21:01:41.290983	22	2024-10-08 00:00:00+00	APTA_939F9701
86	Dave Arenberg	1	2025-06-03 21:03:26.774531	19	2025-02-11 00:00:00+00	APTA_4813F614
53	Ross Freedman	1	2025-06-03 23:19:25.532491	22	2024-10-29 00:00:00+00	APTA_939F9701
51	Ross Freedman	1	2025-05-31 13:37:19.468845	22	2024-10-15 00:00:00+00	APTA_939F9701
54	Ross Freedman	3	2025-05-31 13:37:22.619449	22	2024-11-05 00:00:00+00	APTA_939F9701
55	Ross Freedman	1	2025-05-31 13:37:24.235521	22	2024-11-12 00:00:00+00	APTA_939F9701
49	Ross Freedman	2	2025-06-03 23:20:27.363598	22	2024-10-01 00:00:00+00	APTA_939F9701
62	Ross Freedman	3	2025-06-03 23:20:29.412916	22	2024-10-05 00:00:00+00	APTA_939F9701
59	Ross Freedman	1	2025-05-31 17:34:11.515955	22	2024-08-24 00:00:00+00	APTA_939F9701
60	Ross Freedman	1	2025-05-31 17:37:21.358847	22	2024-08-31 00:00:00+00	APTA_939F9701
61	Ross Freedman	1	2025-05-31 17:37:30.089891	22	2024-09-07 00:00:00+00	APTA_939F9701
56	Ross Freedman	1	2025-05-31 17:37:32.956294	22	2024-09-14 00:00:00+00	APTA_939F9701
57	Ross Freedman	1	2025-05-31 17:43:49.374031	22	2024-09-22 00:00:00+00	APTA_939F9701
58	Ross Freedman	1	2025-05-31 17:43:53.819808	22	2024-09-29 00:00:00+00	APTA_939F9701
75	David Arenberg	1	2025-06-03 20:56:15.482031	19	2025-01-14 00:00:00+00	APTA_4813F614
76	David Arenberg	2	2025-06-03 20:56:17.082071	19	2025-01-21 00:00:00+00	APTA_4813F614
77	David Arenberg	2	2025-06-03 20:56:18.947986	19	2025-01-18 00:00:00+00	APTA_4813F614
78	David Arenberg	1	2025-06-03 20:56:29.479682	19	2025-01-07 00:00:00+00	APTA_4813F614
79	David Arenberg	1	2025-06-03 20:56:43.091153	19	2025-01-11 00:00:00+00	APTA_4813F614
80	David Arenberg	1	2025-06-03 20:58:30.886414	19	2024-09-24 00:00:00+00	APTA_4813F614
81	David Arenberg	2	2025-06-03 20:58:33.086544	19	2024-10-01 00:00:00+00	APTA_4813F614
82	David Arenberg	3	2025-06-03 20:58:34.675945	19	2024-10-05 00:00:00+00	APTA_4813F614
83	David Arenberg	1	2025-06-03 20:59:25.192896	19	2024-10-08 00:00:00+00	APTA_4813F614
85	David Arenberg	3	2025-06-03 21:02:40.951048	19	2025-01-25 00:00:00+00	APTA_4813F614
104	Rosss Freedman	3	2025-06-06 09:37:32.004223	22	2024-12-28 00:00:00+00	\N
126	Ross Freedman	1	2025-06-07 15:10:22.375168	114	2025-07-21 00:00:00+00	\N
105	Ross Freedman	1	2025-06-06 10:45:07.053153	22	2025-02-15 00:00:00+00	\N
106	Ross Freedman	1	2025-06-06 10:48:59.193005	22	2025-02-01 00:00:00+00	\N
107	Ross Freedman	1	2025-06-06 10:49:40.085061	22	2024-09-03 00:00:00+00	\N
108	Ross Freedman	1	2025-06-06 10:49:41.303744	22	2024-09-10 00:00:00+00	\N
109	Ross Freedman	2	2025-06-06 10:49:42.585871	22	2024-09-17 00:00:00+00	\N
110	Ross Freedman	1	2025-06-07 12:46:51.802347	114	2025-06-05 00:00:00+00	\N
48	Ross Freedman	1	2025-06-07 21:46:16.150021	22	2024-09-24 00:00:00+00	APTA_939F9701
96	Rosss Freedman	1	2025-06-07 14:03:48.82424	22	2024-09-24 00:00:00+00	\N
111	Ross Freedman	1	2025-06-07 14:19:55.3332	114	2025-06-12 00:00:00+00	\N
112	Ross Freedman	1	2025-06-07 15:04:31.434985	113	2024-10-01 00:00:00+00	\N
113	Ross Freedman	1	2025-06-07 15:04:42.62873	113	2025-03-15 00:00:00+00	\N
114	Ross Freedman	1	2025-06-07 15:09:16.315022	114	2025-05-26 00:00:00+00	\N
115	Ross Freedman	1	2025-06-07 15:09:18.13582	114	2025-05-29 00:00:00+00	\N
117	Ross Freedman	2	2025-06-07 15:09:42.416634	114	2025-06-09 00:00:00+00	\N
118	Ross Freedman	1	2025-06-07 15:09:46.260489	114	2025-06-16 00:00:00+00	\N
128	Ross Freedman	2	2025-06-07 15:10:28.272077	114	2025-07-17 00:00:00+00	\N
127	Ross Freedman	2	2025-06-07 15:10:29.654546	114	2025-07-24 00:00:00+00	\N
129	Ross Freedman	2	2025-06-07 15:10:33.754581	114	2025-07-28 00:00:00+00	\N
130	Ross Freedman	2	2025-06-07 15:10:35.277698	114	2025-08-04 00:00:00+00	\N
131	Ross Freedman	2	2025-06-07 15:10:39.656552	114	2025-07-31 00:00:00+00	\N
132	Ross Freedman	1	2025-06-07 15:10:45.422625	114	2025-08-07 00:00:00+00	\N
133	Sinan Aktar	1	2025-06-07 15:22:08.613677	22	2025-01-07 00:00:00+00	\N
134	Ross Freedman	2	2025-06-07 20:12:32.308111	22	2025-02-22 00:00:00+00	\N
69	Ross Freedman	1	2025-06-07 20:12:35.413775	22	2025-03-01 00:00:00+00	APTA_939F9701
135	Jeffrey Condren	2	2025-06-08 13:27:28.122507	107	2025-05-29 00:00:00+00	\N
116	Ross Freedman	1	2025-06-07 21:52:02.276842	114	2025-06-02 00:00:00+00	\N
136	Jeffrey Condren	1	2025-06-08 13:28:07.997326	114	2025-06-09 00:00:00+00	\N
137	Jeffrey Condren	1	2025-06-08 13:28:25.623857	114	2025-06-02 00:00:00+00	\N
138	Jeffrey Condren	2	2025-06-08 13:28:28.080277	114	2025-06-16 00:00:00+00	\N
139	Jeffrey Condren	1	2025-06-08 13:28:42.894851	114	2025-06-30 00:00:00+00	\N
140	Rick Lapiana	1	2025-06-08 17:59:16.878452	15	2024-09-25 00:00:00+00	\N
\.


--
-- Data for Name: series; Type: TABLE DATA; Schema: public; Owner: -
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
113	Series 2A
114	Series 2B
\.


--
-- Data for Name: series_leagues; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.series_leagues (id, series_id, league_id, created_at) FROM stdin;
141	11	1	2025-06-07 17:41:14.454555
142	13	1	2025-06-07 17:41:14.610655
143	15	1	2025-06-07 17:41:14.791058
144	17	1	2025-06-07 17:41:14.970612
145	19	1	2025-06-07 17:41:15.128399
146	21	1	2025-06-07 17:41:15.284642
147	22	1	2025-06-07 17:41:15.419501
148	23	1	2025-06-07 17:41:15.622833
149	27	1	2025-06-07 17:41:15.752413
150	29	1	2025-06-07 17:41:15.878703
151	31	1	2025-06-07 17:41:15.999936
152	33	1	2025-06-07 17:41:16.130132
153	35	1	2025-06-07 17:41:16.269985
154	37	1	2025-06-07 17:41:16.418125
155	38	1	2025-06-07 17:41:16.547596
156	6	1	2025-06-07 17:41:16.688233
157	7	1	2025-06-07 17:41:16.822903
158	9	1	2025-06-07 17:41:16.952813
159	105	3	2025-06-07 17:41:17.096574
160	113	3	2025-06-07 17:41:17.235916
161	114	3	2025-06-07 17:41:17.361526
162	107	3	2025-06-07 17:41:17.487996
\.


--
-- Data for Name: user_activity_logs; Type: TABLE DATA; Schema: public; Owner: -
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
13936	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-21 21:55:02.101674
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
13909	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 2024-10-15, Available: 2	\N	2025-05-21 19:05:22.857581
13910	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-21 19:51:41.432909
13911	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	\N	2025-05-21 19:52:01.193379
13912	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 2024-09-24, Available: 2	\N	2025-05-21 19:52:09.679612
13913	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 2024-09-24, Available: 3	\N	2025-05-21 19:52:10.810764
13914	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 2024-10-01, Available: 1	\N	2025-05-21 19:52:11.790502
13915	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 2024-10-01, Available: 2	\N	2025-05-21 19:52:12.8574
13916	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 2024-10-08, Available: 2	\N	2025-05-21 19:52:14.053497
13917	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	Accessed Ask AI page	\N	2025-05-21 19:52:18.758733
13918	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-21 19:52:34.16147
13919	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	\N	2025-05-21 19:52:52.720713
13920	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-21 20:24:40.630602
13921	rossfreedman@gmail.com	auth	\N	login	Successful login	\N	2025-05-21 20:29:55.56043
13922	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-21 20:29:55.923866
13923	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 2024-09-24, Available: 1	\N	2025-05-21 20:30:04.36183
13924	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 2024-10-01, Available: 1	\N	2025-05-21 20:30:05.838373
13925	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 2024-12-10, Available: 2	\N	2025-05-21 20:36:26.395412
13926	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-21 20:36:44.438815
13927	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-21 20:36:47.32583
13928	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Andy Adler	\N	2025-05-21 20:37:24.88234
13929	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-21 20:37:56.835725
13930	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	\N	2025-05-21 20:38:02.050429
13931	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	\N	2025-05-21 20:38:13.775571
13932	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	\N	2025-05-21 20:38:26.002214
13933	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	\N	2025-05-21 20:59:03.618611
13934	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-21 21:53:14.693926
13935	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Joe Schauenberg	\N	2025-05-21 21:54:00.044705
14154	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 13:23:13.57318
13937	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-21 22:16:33.011029
13938	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 00:59:22.77633
13939	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 00:59:27.380979
13940	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 01:11:14.279702
13941	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	\N	2025-05-22 01:11:25.886772
13942	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 01:11:56.179515
13943	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 01:59:09.08594
13944	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	\N	2025-05-22 01:59:13.08991
13945	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	\N	2025-05-22 01:59:31.691076
13946	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	\N	2025-05-22 01:59:47.789348
13947	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 02:00:06.898822
13948	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	\N	2025-05-22 02:01:35.088207
13949	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 03:00:36.239141
13950	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 03:00:39.018267
13951	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 03:00:45.262546
13952	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 03:01:14.961646
13953	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 03:02:27.441105
13954	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 03:23:06.02629
13955	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 03:23:09.909741
13956	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 03:23:58.527506
13957	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	\N	2025-05-22 03:25:05.581197
13958	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	\N	2025-05-22 03:25:55.04201
13959	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	\N	2025-05-22 03:26:13.674177
13960	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 03:26:18.209507
13961	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 2024-09-24, Available: 2	\N	2025-05-22 03:26:28.840489
13962	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 03:26:48.3026
13963	rossfreedman@gmail.com	page_visit	mobile_lineup_escrow	\N	Accessed mobile lineup escrow page	\N	2025-05-22 03:27:06.457032
13964	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 03:27:18.310182
13965	rossfreedman@gmail.com	page_visit	mobile_lineup_escrow	\N	Accessed mobile lineup escrow page	\N	2025-05-22 03:27:28.337898
13966	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 12:49:12.679748
13967	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 12:49:57.052732
13968	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	\N	2025-05-22 12:49:58.799092
13969	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	\N	2025-05-22 12:50:04.61633
13970	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 12:50:07.648859
13971	rossfreedman@gmail.com	page_visit	mobile_lineup_escrow	\N	Accessed mobile lineup escrow page	\N	2025-05-22 13:22:39.366126
13972	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 13:43:50.340059
13973	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 13:43:51.238334
13974	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 13:44:01.070782
13975	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 14:49:39.09458
13976	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 14:49:43.622987
13977	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 14:52:29.940144
13978	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 14:52:32.059696
13979	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 14:52:46.297701
13980	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 14:54:36.441395
13981	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 15:17:59.063298
13982	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 15:18:01.003171
13983	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 15:22:19.242209
13984	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 15:23:19.549204
13985	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 15:26:58.166048
13986	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 17:38:06.041095
13987	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 17:38:09.581145
13988	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	\N	2025-05-22 17:38:13.435328
13989	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 17:39:47.089076
13990	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 17:39:48.759522
13991	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	\N	2025-05-22 17:39:53.680745
13992	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	\N	2025-05-22 17:39:59.967098
13993	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	Accessed Ask AI page	\N	2025-05-22 17:40:02.80545
13994	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 17:41:37.425203
13995	rossfreedman@gmail.com	auth	\N	login	Successful login	\N	2025-05-22 18:12:39.108951
13996	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 18:12:39.390137
13997	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	\N	2025-05-22 18:12:57.078099
13998	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 2024-09-24, Available: 1	\N	2025-05-22 18:13:12.620861
13999	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 2024-10-01, Available: 2	\N	2025-05-22 18:13:14.100268
14000	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 2024-10-08, Available: 3	\N	2025-05-22 18:13:15.636635
14001	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 2024-10-15, Available: 1	\N	2025-05-22 18:13:17.187644
14002	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	\N	2025-05-22 18:13:33.989079
14003	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	Accessed Ask AI page	\N	2025-05-22 18:13:47.704192
14004	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 18:14:55.615095
14005	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	\N	2025-05-22 18:15:43.333272
14006	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Tod Skarecky	\N	2025-05-22 18:16:29.574549
14007	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 18:16:48.52748
14008	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 18:16:52.553223
14009	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	\N	2025-05-22 18:17:04.651057
14010	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 19:01:20.170897
14011	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 20:21:45.688286
14012	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	\N	2025-05-22 20:21:49.03804
14013	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 20:22:14.253035
14014	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 20:22:17.624194
14015	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 20:22:26.375064
14016	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 20:22:28.109051
14017	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 20:23:15.958158
14018	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 20:23:16.050068
14019	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 20:23:18.036241
14020	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	\N	2025-05-22 20:23:28.174712
14021	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 20:23:51.741446
14022	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Mike Lieberman, Date: 2024-09-24, Available: 1	\N	2025-05-22 20:24:36.20786
14023	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Mike Lieberman, Date: 2024-10-01, Available: 1	\N	2025-05-22 20:24:36.867339
14024	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Mike Lieberman, Date: 2024-10-08, Available: 2	\N	2025-05-22 20:24:38.917314
14025	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Mike Lieberman, Date: 2024-10-15, Available: 2	\N	2025-05-22 20:24:40.465886
14026	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Mike Lieberman, Date: 2024-10-22, Available: 3	\N	2025-05-22 20:24:42.196465
14027	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Mike Lieberman, Date: 2024-10-29, Available: 3	\N	2025-05-22 20:24:43.304178
14028	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 20:25:22.4671
14029	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 20:25:46.017761
14030	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 20:25:54.184383
14031	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 20:39:44.784754
14032	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 20:39:49.311182
14033	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-22 20:39:51.881636
14034	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	\N	2025-05-22 20:39:57.577104
14035	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 2024-09-24, Available: 2	\N	2025-05-22 20:40:11.675865
14036	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 2024-09-24, Available: 1	\N	2025-05-22 20:40:13.057347
14037	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	\N	2025-05-22 20:40:27.887814
14038	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-22 20:40:41.905755
14039	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-23 00:28:38.851797
14040	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-23 03:45:08.041557
14041	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-23 03:45:08.988097
14042	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	\N	2025-05-23 03:45:12.486984
14043	rossfreedman@gmail.com	feature_use	\N	update_availability	Player: Ross Freedman, Date: 2024-10-15, Available: 2	\N	2025-05-23 03:45:21.930189
14044	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-23 03:45:29.458432
14045	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	\N	2025-05-23 03:46:02.680048
14046	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-23 03:46:09.835772
14047	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	Accessed Ask AI page	\N	2025-05-23 03:46:12.623804
14048	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	Accessed Ask AI page	\N	2025-05-23 04:15:54.324259
14049	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-23 04:16:00.444741
14050	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	\N	2025-05-23 04:16:07.673273
14051	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	\N	2025-05-23 04:16:24.635022
14052	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-23 04:16:40.514805
14053	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	\N	2025-05-23 04:17:03.772251
14054	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	\N	2025-05-23 04:17:11.415694
14055	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Mike Stensland	\N	2025-05-23 04:17:57.122895
14056	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Mike Stensland	\N	2025-05-23 12:40:25.900823
14057	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-23 12:40:27.035025
14058	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	\N	2025-05-23 12:40:39.333535
14059	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-23 12:40:55.878712
14060	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	\N	2025-05-23 12:41:28.896092
14061	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	\N	2025-05-23 12:41:45.14247
14062	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-23 12:41:48.554724
14063	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	\N	2025-05-23 12:41:51.868663
14064	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-23 13:25:01.057397
14065	rossfreedman@gmail.com	page_visit	admin	\N	\N	\N	2025-05-23 13:25:23.723234
14066	rossfreedman@gmail.com	page_visit	admin	\N	\N	\N	2025-05-23 13:25:25.118233
14067	rossfreedman@gmail.com	page_visit	admin	\N	\N	\N	2025-05-23 13:25:39.13823
14068	rossfreedman@gmail.com	page_visit	admin	\N	\N	\N	2025-05-23 13:25:40.58095
14069	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-23 13:25:45.183406
14070	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	\N	2025-05-23 13:26:05.020963
14071	rossfreedman@gmail.com	page_visit	admin	\N	\N	\N	2025-05-23 13:33:19.018776
14072	rossfreedman@gmail.com	page_visit	admin	\N	\N	\N	2025-05-23 13:33:19.493778
14073	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	\N	2025-05-23 13:33:24.487991
14074	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	\N	2025-05-23 13:33:28.359911
14075	rossfreedman@gmail.com	page_visit	admin	\N	\N	\N	2025-05-23 13:33:45.144681
14076	rossfreedman@gmail.com	page_visit	admin	\N	\N	\N	2025-05-23 13:33:51.019773
14077	rossfreedman@gmail.com	page_visit	admin	\N	\N	\N	2025-05-23 13:33:53.546205
14078	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-23 13:48:55.577162
14079	rossfreedman@gmail.com	page_visit	admin	\N	\N	\N	2025-05-23 13:49:00.160989
14080	rossfreedman@gmail.com	page_visit	admin	\N	\N	\N	2025-05-23 13:49:08.953674
1	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 08:47:11.481412
14081	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-23 13:51:36.732824
14082	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	\N	2025-05-23 13:55:54.518997
14083	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	\N	2025-05-23 15:02:21.639372
14084	rossfreedman@gmail.com	auth	\N	login	Successful login	\N	2025-05-23 18:23:30.383795
14085	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-23 18:23:30.811509
14086	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	\N	2025-05-23 18:23:42.746794
14087	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	Accessed Ask AI page	\N	2025-05-23 18:23:52.100004
14088	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-23 18:23:56.382912
14089	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	\N	2025-05-23 18:24:05.930563
14090	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Greg Shields	\N	2025-05-23 18:24:27.365801
14091	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-23 18:25:08.094819
14092	rossfreedman@gmail.com	auth	\N	login	Successful login	\N	2025-05-23 18:37:14.920466
14093	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-23 18:37:15.250842
14094	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	\N	2025-05-23 18:37:29.812697
14095	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	\N	2025-05-23 18:38:00.801419
14096	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	Accessed Ask AI page	\N	2025-05-23 18:38:39.18379
14097	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	\N	2025-05-23 18:39:37.977359
14098	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	\N	2025-05-23 18:40:17.357698
14099	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-23 18:42:25.664271
14100	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-23 18:42:26.177549
14101	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	Accessed Ask AI page	\N	2025-05-23 18:42:34.932188
14102	rossfreedman@gmail.com	page_visit	mobile_home	\N	Accessed mobile home page	\N	2025-05-23 21:16:01.495047
14103	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	\N	2025-05-23 21:16:07.09149
14104	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	\N	2025-05-23 21:22:20.515883
14105	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	Accessed Ask AI page	\N	2025-05-23 21:22:27.223309
14106	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	\N	166.194.132.38	2025-05-23 23:25:27.830631
14107	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.194.132.38	2025-05-23 23:31:36.749587
14108	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	166.194.132.38	2025-05-23 23:31:44.21291
14109	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.194.132.38	2025-05-23 23:32:14.814806
14110	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.194.132.38	2025-05-23 23:32:36.428911
14111	rossfreedman@gmail.com	page_visit	mobile_lineup_escrow	\N	Accessed mobile lineup escrow page	166.194.132.38	2025-05-23 23:32:43.95856
14112	rossfreedman@gmail.com	page_visit	admin	\N	\N	166.194.132.38	2025-05-23 23:32:59.149077
14113	rossfreedman@gmail.com	page_visit	admin	\N	\N	166.194.132.38	2025-05-23 23:33:00.364812
14114	rossfreedman@gmail.com	page_visit	admin	\N	\N	166.194.132.38	2025-05-23 23:33:05.180667
14115	rossfreedman@gmail.com	page_visit	admin	\N	\N	166.194.132.38	2025-05-23 23:33:10.122925
14116	rossfreedman@gmail.com	page_visit	admin	\N	\N	166.194.132.38	2025-05-23 23:33:10.688647
14117	rossfreedman@gmail.com	admin_action	\N	delete_user	Deleted user: Adam Seyb (aseyb@gmail.com)	166.194.132.38	2025-05-23 23:33:51.058806
14118	rossfreedman@gmail.com	admin_action	\N	delete_user	Deleted user: Adam Seyb (aseyb@aol.com)	166.194.132.38	2025-05-23 23:33:55.832183
14119	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.194.132.38	2025-05-23 23:34:09.802763
14120	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	166.194.132.38	2025-05-23 23:34:16.299988
14121	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	\N	166.194.132.38	2025-05-23 23:34:18.683835
14122	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	\N	73.22.198.26	2025-05-24 01:42:48.94822
14123	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	\N	73.22.198.26	2025-05-24 01:42:52.150025
14124	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 01:42:54.830214
14125	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-05-24 01:43:03.171977
14126	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	\N	73.22.198.26	2025-05-24 01:43:27.653027
14127	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-24 01:43:50.914359
14128	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Adam Hurley	73.22.198.26	2025-05-24 01:44:39.034016
14129	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 01:44:46.630186
14130	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-05-24 01:44:51.281173
14131	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	73.22.198.26	2025-05-24 01:46:11.706843
14132	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 01:46:52.32229
14133	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 01:47:13.666119
14134	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 01:47:17.490305
14135	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-05-24 01:47:25.730634
14136	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 01:47:47.066548
14137	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 01:48:06.265736
14138	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 03:27:10.396036
14139	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 04:01:21.512921
14140	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 04:01:28.508753
14141	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	73.22.198.26	2025-05-24 04:01:30.240486
14142	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 04:03:09.169514
14143	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 04:03:09.526226
14144	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 04:03:37.293423
14145	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	73.22.198.26	2025-05-24 04:03:41.089117
14146	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 04:03:49.359098
14147	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-05-24 04:03:55.634217
14148	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-05-24 04:04:03.21116
14149	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-05-24 04:04:51.330161
14150	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 13:08:43.61316
14151	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-24 13:08:47.534505
14152	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 13:09:08.519788
14153	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	\N	73.22.198.26	2025-05-24 13:23:11.42392
14155	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-24 13:23:19.229328
14156	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 13:23:50.372175
14157	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-24 13:24:09.70596
14158	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-24 13:24:15.513988
14159	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 13:27:57.633531
14160	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-24 13:28:02.878477
14161	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 13:32:30.69618
14162	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	73.22.198.26	2025-05-24 13:32:54.917642
14163	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-24 13:33:05.897679
14164	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-05-24 13:33:20.354265
14165	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 13:33:46.488256
14166	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 13:34:15.087652
14167	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-05-24 20:35:14.217581
14168	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 20:35:14.56943
14169	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-24 20:35:16.918419
14170	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-24 20:36:37.126782
14171	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-24 20:39:15.471692
14172	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 20:49:08.239724
14173	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 20:49:11.756421
14174	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-05-24 20:49:33.752947
14175	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 20:49:34.312265
14176	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	73.22.198.26	2025-05-24 20:49:44.012158
14177	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 20:50:16.972395
14178	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-05-24 20:51:06.312496
14179	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-24 20:51:25.535692
14180	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-24 20:52:53.463028
14181	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-24 20:53:34.918587
14182	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-24 20:54:01.906031
14183	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-24 20:55:06.460142
14184	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-05-24 21:01:10.989945
14185	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 21:01:11.366515
14186	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	73.22.198.26	2025-05-24 21:01:14.616683
14187	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 21:06:20.850307
14188	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-05-24 21:06:43.825253
14189	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 21:06:44.294658
14190	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 21:10:56.716827
14191	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 21:12:17.610481
14192	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-24 21:12:53.286641
14193	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-24 21:13:36.760618
14194	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-24 21:14:09.819929
14195	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-24 21:15:00.653222
14196	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-05-24 22:04:14.629321
14197	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 22:04:15.062831
14198	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-24 22:04:27.413323
14199	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-05-24 22:05:24.021335
14200	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-05-24 22:18:31.570079
14201	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 22:18:31.932921
14202	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-05-24 22:18:39.053933
14203	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-05-24 22:20:38.595562
14204	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 22:20:45.52854
14205	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-05-24 22:20:50.094379
14206	rossfreedman@gmail.com	admin_action	\N	delete_user	Deleted user: Jess Freedman (jessfreedman@gmail.com)	73.22.198.26	2025-05-24 22:20:54.510312
14207	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 22:21:00.841841
14208	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	\N	73.22.198.26	2025-05-24 22:21:07.111227
14209	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-05-24 22:33:13.591848
14210	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 22:39:33.139404
14211	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 22:39:33.424763
14212	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-24 22:41:20.75431
14213	scottosterman@yahoo.com	auth	\N	register	Registration successful	104.28.104.31	2025-05-24 22:56:14.545064
14214	scottosterman@yahoo.com	page_visit	mobile_home	\N	\N	104.28.104.31	2025-05-24 22:56:14.741633
14215	scottosterman@yahoo.com	page_visit	mobile_analyze_me	\N	\N	104.28.104.31	2025-05-24 22:56:31.673292
14216	scottosterman@yahoo.com	page_visit	mobile_view_schedule	\N	Viewed schedule	104.28.104.31	2025-05-24 22:57:28.037529
14217	scottosterman@yahoo.com	page_visit	mobile_improve	\N	Accessed improve page	104.28.104.31	2025-05-24 22:57:33.530678
14218	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.194.132.38	2025-05-25 01:27:08.24977
14219	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	\N	166.194.132.38	2025-05-25 01:27:15.456615
14220	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-25 02:13:03.486225
14221	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 02:13:23.429182
14222	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 02:13:45.846607
14223	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-05-25 02:14:10.157935
14224	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-05-25 02:14:12.07049
14225	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-05-25 02:14:54.722629
14226	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-05-25 09:44:26.031963
14227	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-25 09:44:29.023852
14228	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 09:44:33.548259
14229	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-05-25 09:45:30.950676
14230	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-05-25 09:45:46.048149
14231	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-05-25 09:46:51.659795
14232	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	\N	73.22.198.26	2025-05-25 09:47:14.959184
14233	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 09:47:37.904338
14234	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-25 09:48:14.48756
14235	rossfreedman@gmail.com	page_visit	mobile_ask_ai	\N	\N	73.22.198.26	2025-05-25 09:48:49.938984
14236	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-25 09:49:09.622443
14237	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-05-25 09:49:40.670574
14238	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-05-25 09:50:25.981643
14239	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-05-25 09:50:27.485026
14240	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-05-25 09:50:32.59298
14241	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-25 10:30:56.113351
14242	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 10:31:29.024402
14243	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-25 10:31:52.031275
14244	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 10:33:13.913956
14245	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 10:33:50.845334
14246	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 10:34:58.777805
14247	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-25 10:47:05.568047
14248	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 10:55:12.009417
14249	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-25 11:33:11.707403
14250	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-25 13:29:57.750379
14251	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-05-25 13:30:01.97331
14252	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 13:41:14.071953
14253	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 13:41:20.075029
14254	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-25 13:41:35.982987
14255	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-25 13:41:45.683635
14256	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-25 13:41:45.945163
14257	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-25 13:41:50.132804
14258	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 13:42:26.481692
14259	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-05-25 13:42:41.741602
14260	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-25 13:44:09.638173
14261	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 13:44:16.334842
14262	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-25 13:44:54.162167
14263	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-25 13:45:15.08374
14264	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 13:45:27.37169
14265	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-25 14:15:45.938724
14266	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 14:15:50.115586
14267	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-25 14:16:11.714588
14268	rossfreedman@gmail.com	auth	\N	login	Login successful	73.110.28.143	2025-05-25 15:32:20.629825
14269	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.110.28.143	2025-05-25 15:32:20.99209
14270	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	73.110.28.143	2025-05-25 15:33:13.93311
14271	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.110.28.143	2025-05-25 15:34:08.417438
14272	jmday02@gmail.com	auth	\N	register	Registration successful	73.110.28.143	2025-05-25 15:34:33.195749
14273	jmday02@gmail.com	page_visit	mobile_home	\N	\N	73.110.28.143	2025-05-25 15:34:33.546818
14274	jmday02@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.110.28.143	2025-05-25 15:34:40.066468
14275	jmday02@gmail.com	page_visit	mobile_home	\N	\N	73.110.28.143	2025-05-25 15:35:31.024945
14276	jmday02@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.110.28.143	2025-05-25 15:35:34.956727
14277	jmday02@gmail.com	page_visit	mobile_home	\N	\N	73.110.28.143	2025-05-25 15:38:26.379145
14278	jmday02@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	73.110.28.143	2025-05-25 15:38:28.44572
14279	jmday02@gmail.com	page_visit	mobile_home	\N	\N	73.110.28.143	2025-05-25 15:41:26.291836
14280	jmday02@gmail.com	page_visit	mobile_lineup	\N	\N	73.110.28.143	2025-05-25 15:43:22.069052
14281	jmday02@gmail.com	page_visit	mobile_find_subs	\N	\N	73.110.28.143	2025-05-25 15:44:01.927859
14282	jmday02@gmail.com	page_visit	mobile_lineup_escrow	\N	Accessed mobile lineup escrow page	73.110.28.143	2025-05-25 15:44:24.822586
14283	jmday02@gmail.com	page_visit	mobile_lineup	\N	\N	73.110.28.143	2025-05-25 15:44:30.237321
14284	jmday02@gmail.com	page_visit	mobile_lineup	\N	\N	73.110.28.143	2025-05-25 15:47:29.317744
14285	jmday02@gmail.com	page_visit	mobile_home	\N	\N	73.110.28.143	2025-05-25 15:50:51.918258
14286	jmday02@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.110.28.143	2025-05-25 15:50:57.115546
14287	jmday02@gmail.com	page_visit	mobile_home	\N	\N	73.110.28.143	2025-05-25 15:52:15.727255
14288	jmday02@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.110.28.143	2025-05-25 15:52:27.171513
14289	jmday02@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.110.28.143	2025-05-25 15:53:06.216396
14290	jmday02@gmail.com	page_visit	mobile_home	\N	\N	73.110.28.143	2025-05-25 15:59:11.016369
14291	jmday02@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	73.110.28.143	2025-05-25 15:59:14.159845
14292	jmday02@gmail.com	page_visit	mobile_home	\N	\N	73.110.28.143	2025-05-25 16:06:03.394964
14293	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-05-25 20:31:11.751031
14294	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-25 20:31:14.225579
14295	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 20:31:19.541946
14296	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-25 20:31:33.237978
14297	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-25 22:44:54.162823
14298	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 22:44:57.549457
14299	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-25 22:45:24.716903
14300	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-05-25 22:46:00.519396
14301	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-25 22:52:44.370324
14302	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	73.22.198.26	2025-05-25 22:52:50.452609
14303	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 22:52:58.252989
14304	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-25 22:53:30.58054
14305	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-25 22:53:57.776926
34	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 08:59:31.173288
14306	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 23:35:35.449542
14307	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-25 23:35:38.08273
14308	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-25 23:35:56.217109
14309	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-25 23:36:53.479081
14310	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-25 23:37:37.157511
14311	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-25 23:39:03.319891
14312	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.194.132.38	2025-05-25 23:45:35.956737
14313	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	166.194.132.38	2025-05-25 23:45:37.035204
14314	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	166.194.132.38	2025-05-25 23:45:44.062264
14315	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	166.194.132.38	2025-05-25 23:45:54.315482
14316	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	166.194.132.38	2025-05-25 23:45:57.851736
14317	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	166.194.132.38	2025-05-25 23:46:02.277485
14318	rossfreedman@gmail.com	ai_chat	\N	\N	\N	166.194.132.38	2025-05-25 23:52:38.220138
14319	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	98.46.108.195	2025-05-26 00:23:39.38278
14320	petewahlstom@hotmail.com	auth	\N	register	Registration successful	98.46.108.195	2025-05-26 00:24:58.772444
14321	petewahlstom@hotmail.com	page_visit	mobile_home	\N	\N	98.46.108.195	2025-05-26 00:24:59.133533
14322	petewahlstom@hotmail.com	page_visit	mobile_analyze_me	\N	\N	98.46.108.195	2025-05-26 00:25:04.782639
14323	petewahlstom@hotmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-26 12:34:58.125145
14324	petewahlstom@hotmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	73.22.198.26	2025-05-26 12:35:01.020868
14325	petewahlstom@hotmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-26 12:35:27.657773
14326	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-05-26 12:35:41.147518
14327	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-26 12:35:41.507167
14328	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-05-26 12:35:50.369568
14329	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-05-26 12:35:53.444864
14330	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	73.22.198.26	2025-05-26 12:37:03.31517
14331	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-26 12:37:32.75854
14332	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-26 12:38:01.829527
14333	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-26 12:38:32.625263
14334	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-26 12:44:08.361075
14335	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-26 15:16:48.281018
14336	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-26 18:37:32.983385
14337	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-27 01:38:50.811907
14338	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-27 01:38:51.156762
14339	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	73.22.198.26	2025-05-27 01:38:54.731074
14340	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-27 01:39:04.610751
14341	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-27 15:24:50.441434
14342	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	73.22.198.26	2025-05-27 15:24:51.557644
14343	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-05-27 15:24:55.343505
14344	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-27 17:06:00.917987
14345	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.194.132.38	2025-05-27 17:50:28.281539
14346	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-27 21:20:25.211871
14347	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-27 21:23:11.63428
14348	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-27 21:23:13.149375
14349	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-05-27 21:23:52.350471
14350	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-05-27 21:23:54.551655
14351	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-27 21:24:02.467486
14352	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	207.181.193.82	2025-05-28 18:36:15.551585
14353	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	207.181.193.82	2025-05-28 18:36:19.398733
14354	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	207.181.193.82	2025-05-28 18:36:25.703695
14355	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	207.181.193.82	2025-05-28 18:36:43.903261
14356	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	207.181.193.82	2025-05-28 18:37:06.91492
14357	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	207.181.193.82	2025-05-28 18:37:22.256858
14358	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Jeff Lichtman	207.181.193.82	2025-05-28 18:37:38.911286
14359	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	207.181.193.82	2025-05-28 18:37:45.518991
14360	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	108.147.92.59	2025-05-29 01:17:32.694586
14361	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	108.147.92.59	2025-05-29 01:17:37.005355
14362	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-05-29 15:27:21.828615
14363	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-29 15:27:22.202056
14364	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-05-29 15:27:24.683806
14365	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	73.22.198.26	2025-05-29 15:27:37.561536
14366	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-29 15:27:44.186221
14367	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-29 15:30:52.861058
14368	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-05-29 15:30:54.160694
14369	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-29 15:31:12.283847
14370	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-05-29 15:31:14.189622
14371	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	108.147.92.59	2025-05-30 00:01:51.742949
14372	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 12:53:31.639745
14373	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	73.22.198.26	2025-05-30 12:53:34.113531
14374	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 12:53:49.906675
14375	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-30 12:53:55.453085
14376	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-30 12:54:14.194505
14377	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 12:54:20.098201
14378	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 12:54:23.759922
14379	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-05-30 12:54:25.067158
14380	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	73.22.198.26	2025-05-30 12:54:33.713394
14381	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Andy Adler	73.22.198.26	2025-05-30 12:54:43.04555
14382	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 12:54:47.498417
14383	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-05-30 12:54:53.4913
14384	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 14:11:25.36658
14385	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-05-30 16:28:16.491991
14386	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 16:28:16.583882
14387	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 16:28:22.502282
14388	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-30 16:28:23.807209
14389	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 16:28:25.556986
14390	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 16:28:29.703193
14391	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 16:28:30.347473
14392	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 16:28:34.473281
14393	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-05-30 16:28:36.0906
14394	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 16:28:39.17873
14395	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 16:28:50.356422
14396	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-05-30 16:28:53.875312
14397	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 16:28:57.074394
14398	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 17:02:48.429916
14399	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-05-30 17:05:33.648829
14400	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 17:05:33.708066
14401	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	73.22.198.26	2025-05-30 17:06:49.31574
14402	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-30 17:07:44.021261
14403	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-05-30 17:08:15.903316
14404	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 17:08:33.988728
14405	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-05-30 17:08:43.471862
14406	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-05-30 17:08:48.943243
14407	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	73.22.198.26	2025-05-30 17:09:23.530084
14408	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player David Mehlman	73.22.198.26	2025-05-30 17:10:02.642043
14409	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 17:10:32.042308
14410	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-05-30 17:10:48.502054
14411	rossfreedman@gmail.com	page_visit	mobile_lineup_escrow	\N	Accessed mobile lineup escrow page	73.22.198.26	2025-05-30 17:11:05.238594
14412	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-05-30 17:12:07.349711
14413	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 17:12:34.016491
14414	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 23:41:13.293768
14415	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-05-30 23:41:23.722453
14416	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-30 23:41:23.810184
14417	scottosterman@yahoo.com	auth	\N	login	Login successful	104.28.104.23	2025-05-31 01:46:42.606918
14418	scottosterman@yahoo.com	page_visit	mobile_home	\N	\N	104.28.104.23	2025-05-31 01:46:43.035565
14419	scottosterman@yahoo.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	104.28.104.23	2025-05-31 01:47:06.971426
14420	scottosterman@yahoo.com	page_visit	mobile_view_schedule	\N	Viewed schedule	104.28.104.23	2025-05-31 01:48:59.280627
2	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	73.22.198.26	2025-05-31 08:47:21.183528
35	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 09:11:08.173761
36	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 09:24:24.47101
37	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 12:27:47.673419
38	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 12:38:27.564572
39	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 13:10:21.572033
40	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 13:10:32.334464
41	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 13:37:58.361403
42	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 13:38:46.548399
43	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	73.22.198.26	2025-05-31 14:25:57.374423
44	rossfreedman@gmail.com	page_visit	mobile_lineup_escrow	\N	Accessed mobile lineup escrow page	73.22.198.26	2025-05-31 14:28:15.575806
45	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 14:28:22.371573
46	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 14:28:34.224605
47	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-05-31 14:57:16.727888
48	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 14:57:16.830073
49	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 15:44:27.732035
50	rossfreedman@gmail.com	page_visit	mobile_view_schedule	\N	Viewed schedule	73.22.198.26	2025-05-31 15:44:32.626663
51	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 15:45:02.348929
52	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-05-31 17:26:14.899422
53	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 17:26:15.058237
54	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 17:26:18.066522
55	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 17:26:20.225703
56	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 17:31:29.159048
57	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 17:32:19.962948
58	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-31 17:32:21.719426
59	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 17:32:30.915996
60	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-05-31 17:33:00.353736
61	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	73.22.198.26	2025-05-31 17:33:14.620483
62	rossfreedman@gmail.com	page_visit	mobile_practice_times	\N	\N	73.22.198.26	2025-05-31 17:33:24.652433
63	rossfreedman@gmail.com	practice_times_added	\N	\N	Added 34 practice times for Chicago 22 Saturdays at 10:30 AM starting 2024-08-19	73.22.198.26	2025-05-31 17:33:54.950351
64	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 17:35:29.181994
65	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 17:35:52.496541
66	rossfreedman@gmail.com	page_visit	mobile_practice_times	\N	\N	73.22.198.26	2025-05-31 17:35:54.919025
67	rossfreedman@gmail.com	practice_times_removed	\N	\N	Removed 34 practice times for Chicago 22 at Tennaqua	73.22.198.26	2025-05-31 17:36:00.397458
68	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 17:36:05.525595
69	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 17:36:30.973343
70	rossfreedman@gmail.com	page_visit	mobile_practice_times	\N	\N	73.22.198.26	2025-05-31 17:36:34.710695
71	rossfreedman@gmail.com	practice_times_added	\N	\N	Added 33 practice times for Chicago 22 Saturdays at 9:30 AM starting 2024-08-26	73.22.198.26	2025-05-31 17:36:58.010451
72	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 17:37:00.577528
73	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 17:38:41.499638
74	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 17:38:42.026349
75	rossfreedman@gmail.com	page_visit	mobile_practice_times	\N	\N	73.22.198.26	2025-05-31 17:38:45.782784
76	rossfreedman@gmail.com	practice_times_removed	\N	\N	Removed 33 practice times for Chicago 22 at Tennaqua	73.22.198.26	2025-05-31 17:38:49.411652
77	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 17:38:52.109657
78	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 17:41:03.68238
79	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-05-31 17:41:15.171598
80	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-05-31 17:41:25.042456
81	rossfreedman@gmail.com	page_visit	mobile_practice_times	\N	\N	73.22.198.26	2025-05-31 17:41:33.870802
82	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 17:42:10.66654
83	rossfreedman@gmail.com	page_visit	mobile_practice_times	\N	\N	73.22.198.26	2025-05-31 17:42:13.452388
84	rossfreedman@gmail.com	practice_times_added	\N	\N	Added 33 practice times for Chicago 22 Sundays at 10:00 AM starting 2024-09-01	73.22.198.26	2025-05-31 17:42:32.576686
85	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 17:43:06.066521
86	rossfreedman@gmail.com	page_visit	mobile_practice_times	\N	\N	73.22.198.26	2025-05-31 17:43:08.581802
87	rossfreedman@gmail.com	practice_times_removed	\N	\N	Removed 33 practice times for Chicago 22 at Tennaqua	73.22.198.26	2025-05-31 17:43:11.86541
88	rossfreedman@gmail.com	practice_times_added	\N	\N	Added 30 practice times for Chicago 22 Sundays at 10:41 AM starting 2024-09-22	73.22.198.26	2025-05-31 17:43:38.457269
89	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-05-31 17:43:40.369101
90	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-05-31 17:44:42.177971
91	rossfreedman@gmail.com	ai_chat	\N	\N	\N	108.147.92.59	2025-05-31 17:55:28.538373
92	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	108.147.92.59	2025-05-31 17:59:47.577008
93	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 10:29:44.078385
94	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 10:32:30.77125
95	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 10:32:48.398853
96	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-01 10:32:50.304834
97	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-01 10:33:34.18533
98	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-01 10:36:31.300812
99	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	108.147.92.59	2025-06-01 11:08:01.549454
100	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	108.147.92.59	2025-06-01 11:08:14.687829
101	rossfreedman@gmail.com	auth	\N	login	Login successful	107.77.208.231	2025-06-01 11:18:50.47949
102	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	107.77.208.231	2025-06-01 11:18:50.666568
103	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	107.77.208.231	2025-06-01 11:19:15.134784
104	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	107.77.208.231	2025-06-01 11:19:19.833575
105	rossfreedman@gmail.com	page_visit	mobile_practice_times	\N	\N	107.77.208.231	2025-06-01 11:19:28.106871
106	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	107.77.208.231	2025-06-01 11:19:38.832984
107	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	107.77.208.231	2025-06-01 11:19:47.446396
108	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	108.147.92.59	2025-06-01 12:16:05.543515
109	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	108.147.92.59	2025-06-01 12:20:42.24283
110	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	108.147.92.59	2025-06-01 12:20:57.562877
111	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	108.147.92.59	2025-06-01 12:21:45.679808
112	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	108.147.92.59	2025-06-01 12:44:32.704602
113	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	108.147.92.59	2025-06-01 12:44:45.750145
114	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	108.147.92.59	2025-06-01 12:44:51.081976
115	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	108.147.92.59	2025-06-01 12:46:22.756647
116	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	108.147.92.59	2025-06-01 12:46:24.345016
117	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	98.46.110.63	2025-06-01 13:47:34.063689
118	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	108.147.92.59	2025-06-01 13:54:28.698346
119	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	108.147.92.59	2025-06-01 13:54:38.31309
120	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 15:10:30.942524
121	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-01 15:10:52.278693
122	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 15:19:44.435108
123	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-01 15:20:06.14747
124	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-01 15:23:25.523267
125	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-01 15:29:32.329954
126	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-01 15:30:18.289486
127	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-01 15:30:21.460549
128	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-01 15:40:22.07389
129	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 15:47:40.901786
130	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 15:47:44.675009
131	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-01 15:47:48.729726
132	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-01 15:59:08.075035
133	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-06-01 15:59:43.197599
134	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-06-01 15:59:44.315506
135	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-01 16:00:03.577299
136	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-01 16:01:26.433979
137	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-01 16:01:52.354554
138	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-06-01 16:02:14.475246
139	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 16:09:48.475599
140	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 16:09:48.592835
141	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 16:09:48.616462
142	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-01 16:09:54.767963
143	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-01 16:54:37.072135
144	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 19:10:48.833089
145	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 19:13:47.683641
146	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 19:14:06.251913
147	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 19:16:58.287418
148	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-01 19:17:02.298263
149	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 19:17:17.073756
150	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 19:17:17.195271
151	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 19:17:17.379757
152	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-01 19:17:19.216407
153	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 19:17:25.489005
154	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-01 19:17:27.79302
155	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 19:18:02.028466
156	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-01 19:18:03.764345
157	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-06-01 19:18:31.914492
158	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 19:18:42.938964
159	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 19:18:43.507246
160	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 19:41:59.381261
161	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-01 19:42:00.557517
162	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-06-01 19:42:23.406509
163	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-01 21:31:29.769618
164	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-02 06:57:03.85009
165	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-02 06:58:02.331442
166	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-02 06:58:41.834759
167	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	73.22.198.26	2025-06-02 06:59:07.052766
168	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-02 07:00:00.433943
169	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-02 07:00:05.297291
170	rossfreedman@gmail.com	page_visit	mobile_lineup_escrow	\N	Accessed mobile lineup escrow page	73.22.198.26	2025-06-02 07:00:15.884988
171	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-06-02 07:00:17.978612
172	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-02 07:02:19.263098
173	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-02 07:02:24.242571
174	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-02 07:03:52.873312
175	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-02 07:04:54.658533
176	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-02 07:05:23.807179
177	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-02 07:06:04.113067
178	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-02 07:08:17.859718
179	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-02 07:10:52.125353
180	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	108.147.92.59	2025-06-02 07:49:11.72883
181	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	108.147.92.59	2025-06-02 07:49:13.001907
182	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	108.147.92.59	2025-06-02 07:49:19.998639
183	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	108.147.92.59	2025-06-02 07:50:02.647068
184	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Scott Blomquist	108.147.92.59	2025-06-02 07:50:43.106022
185	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	108.147.92.59	2025-06-02 07:50:53.046963
186	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	108.147.92.59	2025-06-02 07:50:55.597068
187	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	108.147.92.59	2025-06-02 07:52:31.292
188	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-02 09:21:12.19941
189	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-02 09:45:26.875336
190	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	108.147.92.59	2025-06-02 11:17:56.740946
191	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	108.147.92.59	2025-06-02 11:17:57.028138
192	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	108.147.92.59	2025-06-02 13:32:11.657923
193	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-02 13:35:47.072005
194	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-02 14:41:19.473726
195	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-02 15:24:52.318963
196	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-02 15:24:56.626364
197	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-02 16:04:54.184773
198	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-02 16:04:56.079538
199	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Eric Lunt	73.22.198.26	2025-06-02 16:05:24.733985
200	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Eric Lunt	73.22.198.26	2025-06-02 16:05:27.808179
201	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-02 16:05:39.59759
202	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-02 16:06:04.328798
203	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-02 16:18:55.376613
204	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-06-02 16:19:21.694481
205	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-06-02 16:19:46.924463
206	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	108.147.92.59	2025-06-02 16:45:59.917518
207	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	108.147.92.59	2025-06-02 17:29:22.685208
208	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-02 22:21:36.028816
209	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-02 22:22:02.104577
210	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-02 22:22:21.799144
211	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-02 22:22:36.603153
212	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	73.22.198.26	2025-06-02 22:22:45.271065
213	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-02 22:23:23.974269
214	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-06-02 22:23:26.265159
215	rossfreedman@gmail.com	page_visit	mobile_lineup_escrow	\N	Accessed mobile lineup escrow page	73.22.198.26	2025-06-02 22:23:28.951213
216	rossfreedman@gmail.com	page_visit	mobile_practice_times	\N	\N	73.22.198.26	2025-06-02 22:23:31.949436
217	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-03 14:19:06.092307
218	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 14:19:06.171972
219	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-03 14:19:34.542597
220	rossfreedman@gmail.com	player_search	\N	\N	Searched for player: brian wagner, found: True	73.22.198.26	2025-06-03 14:19:49.303151
221	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player brian wagner	73.22.198.26	2025-06-03 14:19:49.472821
222	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 14:19:58.340962
223	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-03 14:32:13.940165
224	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 14:32:14.060038
225	rossfreedman@gmail.com	player_search	\N	\N	Searched for player: scott osterman, found: False	73.22.198.26	2025-06-03 14:32:22.880658
226	rossfreedman@gmail.com	player_search	\N	\N	Searched for player: brian wagner, found: True	73.22.198.26	2025-06-03 14:32:28.405449
227	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player brian wagner	73.22.198.26	2025-06-03 14:32:28.753889
228	rossfreedman@gmail.com	player_search	\N	\N	Searched for player: scott osterman, found: False	73.22.198.26	2025-06-03 14:35:47.781216
229	rossfreedman@gmail.com	player_search	\N	\N	Searched for player: Brian Wagner, found: True	73.22.198.26	2025-06-03 14:35:51.639419
230	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Brian Wagner	73.22.198.26	2025-06-03 14:35:51.857348
231	rossfreedman@gmail.com	player_search	\N	\N	Searched for player: Pete Katai, found: False	73.22.198.26	2025-06-03 14:36:06.392758
232	rossfreedman@gmail.com	player_search	\N	\N	Searched for player: Peter Katai, found: True	73.22.198.26	2025-06-03 14:36:08.817454
233	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Peter Katai	73.22.198.26	2025-06-03 14:36:09.121887
234	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 19:49:45.842649
235	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-03 19:49:47.757158
236	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 20:35:30.713976
237	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-03 20:36:32.98445
238	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 20:36:49.416284
239	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-03 20:45:58.372141
240	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 20:45:58.457458
241	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "Dau", found 0 matches	73.22.198.26	2025-06-03 20:46:04.172327
242	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "Day", found 0 matches	73.22.198.26	2025-06-03 20:46:07.675189
243	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "statkus", found 1 matches	73.22.198.26	2025-06-03 20:46:12.103678
244	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 20:47:02.202422
245	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 20:47:18.611156
246	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-03 20:47:20.813289
247	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-03 20:47:30.114328
248	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 20:47:44.160848
249	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 20:47:45.62979
250	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-03 20:47:47.60664
251	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 20:47:59.583715
252	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	73.22.198.26	2025-06-03 20:48:03.851321
253	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Dave Sulkin	73.22.198.26	2025-06-03 20:48:14.591884
254	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 20:48:20.443258
255	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 20:48:20.48963
256	darenberg@gmail.com	auth	\N	register	Registration successful. Matched to Player ID: APTA_4813F614	73.22.198.26	2025-06-03 20:55:47.848462
257	darenberg@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 20:55:47.938719
258	darenberg@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-03 20:55:54.88206
259	darenberg@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 20:56:50.878539
260	darenberg@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 20:56:51.591898
261	darenberg@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 20:57:34.280511
262	darenberg@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-03 20:57:39.191685
263	darenberg@gmail.com	page_visit	mobile_practice_times	\N	\N	73.22.198.26	2025-06-03 20:57:50.232386
264	darenberg@gmail.com	practice_times_removed	\N	\N	Removed 0 practice times for Chicago 19 at Tennaqua	73.22.198.26	2025-06-03 20:57:54.81876
265	darenberg@gmail.com	practice_times_added	\N	\N	Added 28 practice times for Chicago 19 Sundays at 8:58 PM starting 2024-09-30	73.22.198.26	2025-06-03 20:58:11.662389
266	darenberg@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-03 20:58:42.762681
267	darenberg@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 20:59:30.652156
268	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-03 21:00:06.216238
269	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 21:00:06.333576
270	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 21:01:49.989468
271	darenberg@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-03 21:02:06.156416
272	darenberg@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 21:02:06.299304
273	darenberg@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 21:03:02.784377
274	darenberg@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 23:13:47.451529
275	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-03 23:14:02.903747
276	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 23:14:03.0536
277	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 23:14:49.060004
278	rossfreedman@gmail.com	player_search	\N	\N	Searched for "Ross F", found 0 matches	73.22.198.26	2025-06-03 23:14:59.776629
279	rossfreedman@gmail.com	player_search	\N	\N	Searched for "Ross Freedman", found 1 matches	73.22.198.26	2025-06-03 23:15:04.228192
280	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "Freedman", found 1 matches	73.22.198.26	2025-06-03 23:15:11.636074
281	rossfreedman@gmail.com	player_search	\N	\N	Searched for first name "Pete", found 33 matches	73.22.198.26	2025-06-03 23:18:39.857273
282	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Pete Wahlstrom	73.22.198.26	2025-06-03 23:18:45.34231
283	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 23:19:07.993519
284	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 23:20:32.306199
285	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 23:20:32.942532
286	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 23:21:01.323077
287	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-03 23:21:03.314321
288	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 23:21:31.751965
289	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-03 23:21:40.933631
290	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 23:21:41.082117
291	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-03 23:21:43.193697
292	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-03 23:22:25.465955
293	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Will Raider	73.22.198.26	2025-06-03 23:22:43.217763
294	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 23:23:00.031748
295	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-03 23:23:05.28269
296	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Will Raider	73.22.198.26	2025-06-03 23:23:25.163087
297	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 23:23:29.562537
298	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	Accessed mobile my series page	73.22.198.26	2025-06-03 23:23:33.410587
299	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 23:23:36.911919
300	rossfreedman@gmail.com	page_visit	mobile_practice_times	\N	\N	73.22.198.26	2025-06-03 23:23:48.400697
301	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 23:23:54.138434
302	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-03 23:24:06.514515
303	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-04 07:12:19.799608
304	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-04 07:12:57.686859
305	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-04 07:12:59.357152
306	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-04 07:13:14.973069
307	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-04 07:13:27.700203
308	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-04 08:37:01.401613
309	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-04 08:37:07.144048
310	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-04 08:37:12.454976
311	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-04 08:37:50.869384
312	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-04 08:38:14.153198
313	afranger@gmail.com	auth	\N	register	Registration successful. Matched to Player ID: APTA_DE52ECF6	73.22.198.26	2025-06-04 08:39:38.267059
314	afranger@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-04 08:39:38.334355
315	afranger@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-04 08:40:39.772147
316	afranger@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-04 08:40:54.369141
317	afranger@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-04 08:42:25.803525
318	afranger@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-04 08:42:30.926987
319	afranger@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-04 08:44:57.615808
320	afranger@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-04 08:44:59.385142
321	afranger@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-04 08:45:00.384449
322	afranger@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-04 10:38:58.777458
323	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-04 22:47:29.543434
324	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "Samson", found 1 matches	73.22.198.26	2025-06-04 22:47:42.433839
325	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Ken Samson	73.22.198.26	2025-06-04 22:47:52.139455
326	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "Samson", found 1 matches	73.22.198.26	2025-06-04 22:48:07.552711
327	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Ken Samson	73.22.198.26	2025-06-04 22:48:10.929105
328	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 06:08:22.073664
329	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-05 15:51:14.948903
330	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 15:51:15.019203
331	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 15:51:22.738054
332	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.94	2025-06-05 17:30:14.28127
333	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 21:09:49.443072
334	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-05 21:09:56.815541
335	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 21:09:56.95105
336	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-05 21:09:59.277918
337	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2024-09-24 to status 2	73.22.198.26	2025-06-05 21:10:02.668044
338	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2024-09-24 to status 1	73.22.198.26	2025-06-05 21:10:03.658844
339	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-05 21:10:06.722194
340	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-02-25 to status 1	73.22.198.26	2025-06-05 21:10:11.54595
341	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-05 21:10:15.100821
342	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-05 21:10:20.506664
343	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-05 21:10:37.403704
344	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-05 21:10:40.964624
345	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-05 21:10:53.612522
346	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-05 21:10:58.661147
347	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-05 21:11:06.71252
348	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 21:14:39.20884
349	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-05 21:14:40.838204
350	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "freed", found 2 matches	73.22.198.26	2025-06-05 21:14:43.93071
351	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-05 21:14:43.947061
352	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Ross Freedman	73.22.198.26	2025-06-05 21:14:46.316054
353	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 21:14:56.715001
354	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-05 21:14:59.103959
355	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 21:15:05.63883
356	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 21:27:56.99694
357	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-05 21:27:59.417473
358	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-05 21:28:02.907455
359	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-03-04 to status 2	73.22.198.26	2025-06-05 21:28:06.979714
360	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-05 21:28:10.428663
361	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-05 21:28:27.99027
362	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-05 21:31:59.282063
363	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 21:33:22.341522
364	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-05 21:33:24.846135
365	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 21:34:46.222139
366	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-05 21:34:49.988319
367	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 21:34:50.05933
368	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-05 21:34:54.130275
369	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 21:35:30.561698
370	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-05 21:35:31.713547
371	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 21:36:10.616763
372	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-05 21:36:46.146732
373	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 21:36:46.227965
374	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-05 21:36:48.596613
375	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-05 23:14:50.002734
376	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 23:14:50.187844
377	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-05 23:14:56.648459
378	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 23:15:37.949823
379	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-05 23:15:40.847999
380	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-02-11 to status 2	73.22.198.26	2025-06-05 23:15:44.971309
381	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-05 23:15:48.128555
382	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-05 23:15:57.982914
383	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-05 23:16:01.303684
384	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-05 23:16:06.174603
385	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "Day", found 2 matches	73.22.198.26	2025-06-05 23:16:10.587056
386	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-05 23:16:10.60485
387	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Pete Day	73.22.198.26	2025-06-05 23:16:14.244213
388	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 23:16:32.799834
389	rossfreedman@gmail.com	page_visit	mobile_team_schedule	\N	\N	73.22.198.26	2025-06-05 23:16:46.825336
390	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 23:17:14.498991
391	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-05 23:17:27.993298
392	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 23:17:33.249309
393	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-05 23:17:38.103348
394	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-05 23:17:44.4494
395	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 23:17:48.831451
396	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-05 23:17:52.306075
397	Rosss Freedman	availability_update	mobile_availability	\N	Set availability for 2024-09-24 to status 2	73.22.198.26	2025-06-05 23:17:53.704415
398	Rosss Freedman	availability_update	mobile_availability	\N	Set availability for 2024-09-24 to status 1	73.22.198.26	2025-06-05 23:17:54.68354
399	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-05 23:17:57.877628
400	Rosss Freedman	availability_update	mobile_availability	\N	Set availability for 2024-10-15 to status 2	73.22.198.26	2025-06-05 23:18:05.861106
401	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-05 23:18:09.580754
402	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-05 23:18:14.690536
403	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-05 23:18:20.208637
404	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 23:18:53.210235
405	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-05 23:18:54.899834
406	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-05 23:19:00.485508
407	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 23:19:06.022545
408	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-05 23:19:08.59834
409	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-05 23:19:20.831987
410	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 23:19:27.437173
411	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-05 23:19:28.555988
412	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-05 23:19:34.722186
413	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 23:19:40.098559
414	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-05 23:19:44.205157
415	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-05 23:19:51.410529
416	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-05 23:19:59.92441
417	rossfreedman@gmail.com	page_visit	mobile_team_schedule	\N	\N	73.22.198.26	2025-06-05 23:20:09.845912
418	rossfreedman@gmail.com	page_visit	mobile_practice_times	\N	\N	73.22.198.26	2025-06-05 23:20:22.209761
419	rossfreedman@gmail.com	practice_times_added	\N	\N	Added 32 practice times for Chicago 22 Saturdays at 11:20 PM starting 2024-09-01	73.22.198.26	2025-06-05 23:20:39.662217
420	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-05 23:20:46.615241
421	Rosss Freedman	availability_update	mobile_availability	\N	Set availability for 2024-09-14 to status 2	73.22.198.26	2025-06-05 23:20:52.820438
422	Rosss Freedman	availability_update	mobile_availability	\N	Set availability for 2024-09-21 to status 1	73.22.198.26	2025-06-05 23:20:55.178343
423	Rosss Freedman	availability_update	mobile_availability	\N	Set availability for 2024-09-24 to status 2	73.22.198.26	2025-06-05 23:20:57.374739
424	Rosss Freedman	availability_update	mobile_availability	\N	Set availability for 2024-09-07 to status 2	73.22.198.26	2025-06-05 23:21:02.332941
425	rossfreedman@gmail.com	page_visit	mobile_all_team_availability	\N	\N	73.22.198.26	2025-06-05 23:21:03.203864
426	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 23:21:08.06512
427	rossfreedman@gmail.com	page_visit	mobile_team_schedule	\N	\N	73.22.198.26	2025-06-05 23:21:20.472177
428	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-05 23:22:07.937147
429	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 23:22:08.126156
430	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-06-05 23:22:20.228803
431	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-06-05 23:22:23.324071
432	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-06-05 23:22:24.373145
433	rossfreedman@gmail.com	page_visit	mobile_reserve_court	\N	\N	73.22.198.26	2025-06-05 23:23:03.568283
434	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-05 23:23:06.065205
435	rossfreedman@gmail.com	ai_chat	\N	\N	\N	73.22.198.26	2025-06-05 23:23:30.454396
436	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-05 23:23:52.241341
437	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-05 23:24:02.487537
438	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 06:17:35.661504
439	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-06 06:17:40.401602
440	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-06 06:17:45.163617
441	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-06 06:17:48.777243
442	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-06 06:17:56.93049
443	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-06 06:17:59.067229
444	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-06 06:18:01.616101
445	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 06:18:09.676385
446	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-06 06:18:11.892633
447	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "freed", found 2 matches	73.22.198.26	2025-06-06 06:18:14.03542
448	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-06 06:18:14.051768
449	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 06:18:15.676531
450	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-06 06:18:17.454652
451	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 06:18:20.632173
452	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-06 06:18:22.794997
453	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 06:18:27.352163
454	rossfreedman@gmail.com	page_visit	mobile_team_schedule	\N	\N	73.22.198.26	2025-06-06 06:18:30.321438
455	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 06:18:56.077499
456	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-06 06:19:02.375667
457	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-06-06 06:19:07.80509
458	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 06:20:54.141184
459	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-06-06 06:28:21.624524
460	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 06:28:44.305678
461	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-06 06:28:46.112731
462	rossfreedman@gmail.com	page_visit	admin	\N	\N	73.22.198.26	2025-06-06 08:00:49.108945
463	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 08:01:01.269134
464	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-06 08:01:05.089037
465	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 08:01:10.81401
466	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-06 08:01:12.215727
467	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 08:01:26.624669
468	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-06 08:01:27.622288
469	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 08:01:31.296084
470	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-06 08:01:32.411364
471	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 08:01:39.826153
472	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-06 08:01:41.397283
473	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 08:01:46.601752
474	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-06 08:01:47.548224
475	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 08:01:54.866497
476	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-06 08:01:56.84634
477	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-06 08:01:58.945856
478	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Field Stern	73.22.198.26	2025-06-06 08:02:01.805222
479	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 08:03:42.682469
480	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-06 08:03:43.905504
481	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 08:04:37.751841
482	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-06-06 08:05:33.709231
483	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 08:06:01.346868
484	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-06 08:06:05.291903
485	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-03-08 to status 1	73.22.198.26	2025-06-06 08:06:09.660608
486	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 08:06:14.189529
487	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-06 08:06:17.586032
488	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 08:06:28.090613
489	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.94	2025-06-06 09:09:00.995837
490	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	166.199.152.94	2025-06-06 09:09:19.884954
491	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	166.199.152.94	2025-06-06 09:09:24.493493
492	rossfreedman@gmail.com	page_visit	mobile_reserve_court	\N	\N	166.199.152.94	2025-06-06 09:09:30.979305
493	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	166.199.152.94	2025-06-06 09:09:32.927773
494	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	166.199.152.94	2025-06-06 09:09:37.211855
495	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.94	2025-06-06 09:09:38.873951
496	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	166.199.152.94	2025-06-06 09:09:42.696299
497	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	166.199.152.94	2025-06-06 09:09:54.487229
498	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	166.199.152.94	2025-06-06 09:10:03.480767
499	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	166.199.152.94	2025-06-06 09:10:09.881395
500	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.94	2025-06-06 09:36:47.283409
501	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	166.199.152.94	2025-06-06 09:37:07.13102
502	Rosss Freedman	availability_update	mobile_availability	\N	Set availability for 2024-10-15 to status 2	166.199.152.94	2025-06-06 09:37:11.29193
503	Rosss Freedman	availability_update	mobile_availability	\N	Set availability for 2024-10-15 to status 3	166.199.152.94	2025-06-06 09:37:12.112824
504	Rosss Freedman	availability_update	mobile_availability	\N	Set availability for 2024-10-08 to status 3	166.199.152.94	2025-06-06 09:37:13.998611
505	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	166.199.152.94	2025-06-06 09:37:24.149403
506	Rosss Freedman	availability_update	mobile_availability	\N	Set availability for 2025-01-21 to status 3	166.199.152.94	2025-06-06 09:37:29.402266
507	Rosss Freedman	availability_update	mobile_availability	\N	Set availability for 2024-12-28 to status 3	166.199.152.94	2025-06-06 09:37:32.02204
508	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	166.199.152.94	2025-06-06 09:37:36.150238
509	rossfreedman@gmail.com	page_visit	mobile_reserve_court	\N	\N	166.199.152.94	2025-06-06 09:37:54.486647
510	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	166.199.152.94	2025-06-06 09:38:03.673582
511	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	166.199.152.94	2025-06-06 09:38:17.977443
512	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	166.199.152.94	2025-06-06 09:38:25.894816
513	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	166.199.152.94	2025-06-06 09:38:36.691788
514	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	166.199.152.94	2025-06-06 09:38:39.184651
515	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	166.199.152.94	2025-06-06 09:38:46.675148
516	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Daniel Caldwell	166.199.152.94	2025-06-06 09:38:57.79353
517	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.94	2025-06-06 09:39:05.18321
518	rossfreedman@gmail.com	page_visit	mobile_lineup_escrow	\N	Accessed mobile lineup escrow page	166.199.152.94	2025-06-06 09:39:06.244066
519	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	166.199.152.94	2025-06-06 09:39:08.589426
520	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.94	2025-06-06 10:12:00.980869
521	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:44:50.907574
522	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-06 10:44:54.283969
523	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2024-09-24 to status 2	73.22.198.26	2025-06-06 10:44:56.828523
524	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:44:58.7473
525	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-06 10:45:01.781878
526	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-02-15 to status 1	73.22.198.26	2025-06-06 10:45:07.075089
527	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:45:08.404864
528	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-06 10:45:09.472375
529	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:45:16.577628
530	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-06 10:45:20.028031
531	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:45:27.139957
532	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-06 10:45:28.209561
533	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:45:29.634592
534	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-06 10:45:31.075457
535	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:45:32.633851
536	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-06 10:45:34.053387
537	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:45:40.117063
538	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-06 10:45:42.96619
539	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "hanover", found 1 matches	73.22.198.26	2025-06-06 10:45:49.620576
540	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-06 10:45:49.639762
541	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Brian Hanover	73.22.198.26	2025-06-06 10:45:52.129959
542	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:45:54.009554
543	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-06 10:45:56.324525
544	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:45:59.034969
545	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-06-06 10:46:02.50966
546	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-06-06 10:46:48.539678
547	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:48:45.025759
548	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-06 10:48:52.969623
549	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-02-01 to status 1	73.22.198.26	2025-06-06 10:48:59.214165
550	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:49:00.88183
551	rossfreedman@gmail.com	page_visit	mobile_practice_times	\N	\N	73.22.198.26	2025-06-06 10:49:02.857717
552	rossfreedman@gmail.com	practice_times_removed	\N	\N	Removed 19 practice times for Chicago 22 at Tennaqua	73.22.198.26	2025-06-06 10:49:06.096568
553	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:49:08.814016
554	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:49:09.204902
555	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-06 10:49:12.127315
556	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:49:15.911668
557	rossfreedman@gmail.com	page_visit	mobile_practice_times	\N	\N	73.22.198.26	2025-06-06 10:49:17.043168
558	rossfreedman@gmail.com	practice_times_added	\N	\N	Added 33 practice times for Chicago 22 Tuesdays at 6:00 PM starting 2024-09-03	73.22.198.26	2025-06-06 10:49:32.152351
559	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-06 10:49:37.216664
560	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2024-09-03 to status 1	73.22.198.26	2025-06-06 10:49:40.10504
561	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2024-09-10 to status 1	73.22.198.26	2025-06-06 10:49:41.321683
562	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2024-09-17 to status 2	73.22.198.26	2025-06-06 10:49:42.602222
563	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:50:57.41539
564	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-06 10:51:02.032084
565	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:51:06.081211
566	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-06 10:51:07.349156
567	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:57:10.830162
568	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-06-06 10:57:18.377177
569	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-06-06 10:57:56.265123
570	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 10:58:34.027221
571	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-06-06 10:58:38.415842
572	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 11:05:22.766758
573	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-06 11:07:07.932608
574	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 11:14:40.236309
575	bfox@aol.com	auth	\N	register	Registration successful. No Player ID match found	73.22.198.26	2025-06-06 11:15:07.194436
576	bfox@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 11:15:07.499607
577	bfox@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-06 11:15:12.649396
578	bfox@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 11:15:23.700718
579	bfox@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-06 11:15:25.880802
580	bfox@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-06 11:15:57.731546
581	bfox@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 11:15:59.435381
582	bfox@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-06 11:16:02.10831
583	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-06 16:42:53.02038
584	bfox@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 10:01:57.246854
585	bfox@aol.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-07 10:02:00.775566
586	bfox@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 10:02:05.544755
587	bfox@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 10:02:10.448111
588	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-07 12:13:09.880413
589	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:13:09.940209
590	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-07 12:13:14.29047
591	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-07 12:13:22.345186
592	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 12:13:29.184897
593	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-07 12:13:33.002242
594	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-07 12:13:41.584948
595	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-07 12:13:48.901914
596	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-07 12:13:53.077918
597	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:13:57.086863
598	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 12:13:57.952171
599	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:17:07.587693
600	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-07 12:17:09.796067
601	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:17:18.176745
602	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:17:18.196497
603	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:17:18.532012
604	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 12:17:20.010894
605	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:17:41.266231
606	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-07 12:17:45.84779
607	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:17:45.941099
608	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 12:17:47.160048
609	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 12:18:34.795945
610	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:28:59.239934
611	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-07 12:29:04.008846
612	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:29:04.603608
613	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-07 12:29:06.588318
614	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 12:29:09.766872
615	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:34:18.998552
616	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-07 12:34:22.719069
617	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:34:22.830437
618	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 12:34:23.798406
619	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 12:37:15.145365
620	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 12:41:39.41994
621	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 12:41:50.996272
622	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:41:51.959156
623	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 12:41:54.377014
624	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-07 12:42:00.649966
625	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-07 12:42:10.728863
626	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 12:42:15.728877
627	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 12:42:20.609291
628	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:42:22.267381
629	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-07 12:42:23.408023
630	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:42:26.523695
631	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-07 12:42:29.631602
632	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-07 12:42:40.149363
633	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:46:38.896992
634	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:46:38.915215
635	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-07 12:46:42.30687
636	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-07 12:46:46.66675
637	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-06-05 to status 1	73.22.198.26	2025-06-07 12:46:51.824229
638	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 12:46:55.679328
639	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 12:47:05.102941
640	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:47:05.433842
641	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-07 12:47:09.838111
642	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2024-09-24 to status 1	73.22.198.26	2025-06-07 12:47:15.568554
643	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-07 12:47:19.221355
644	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 12:47:23.556848
645	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 12:47:27.353708
646	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-07 12:48:24.414686
647	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-07 14:03:38.046387
648	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	166.199.152.86	2025-06-07 14:03:43.831805
649	Rosss Freedman	availability_update	mobile_availability	\N	Set availability for 2024-09-24 to status 1	166.199.152.86	2025-06-07 14:03:48.842142
650	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	166.199.152.86	2025-06-07 14:03:54.471882
651	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-07 14:04:02.174277
652	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-07 14:04:10.084566
653	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-07 14:04:22.292728
654	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-07 14:04:22.49857
655	rossfreedman@gmail.com	auth	\N	login	Login successful	166.199.152.86	2025-06-07 14:04:34.940275
656	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-07 14:04:35.41144
657	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-07 14:04:38.818638
658	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	166.199.152.86	2025-06-07 14:04:50.240229
659	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-07 14:04:58.301861
660	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-07 14:04:58.479793
661	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-07 14:05:04.161144
662	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-07 14:05:24.513989
663	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-07 14:05:29.344038
664	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	166.199.152.86	2025-06-07 14:05:32.635448
665	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	166.199.152.86	2025-06-07 14:05:40.028225
666	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	166.199.152.86	2025-06-07 14:05:55.296274
667	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	166.199.152.86	2025-06-07 14:06:17.166714
668	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	166.199.152.86	2025-06-07 14:06:21.954309
669	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-07 14:06:45.534232
670	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-07 14:06:56.222196
671	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	166.199.152.86	2025-06-07 14:07:12.084914
672	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	166.199.152.86	2025-06-07 14:07:25.842639
673	rossfreedman@gmail.com	player_search	\N	\N	Searched for first name "Ross", found 9 matches	166.199.152.86	2025-06-07 14:07:43.036454
674	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	166.199.152.86	2025-06-07 14:07:43.052055
675	rossfreedman@gmail.com	player_search	\N	\N	Searched for first name "Sridar", found 0 matches	166.199.152.86	2025-06-07 14:07:52.676378
676	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	166.199.152.86	2025-06-07 14:07:52.693382
677	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-07 14:07:56.140144
678	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-07 14:07:56.206943
679	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	166.199.152.86	2025-06-07 14:08:08.497493
680	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-07 14:19:32.601255
681	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	166.199.152.86	2025-06-07 14:19:42.932552
682	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-06-12 to status 1	166.199.152.86	2025-06-07 14:19:55.350291
683	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	166.199.152.86	2025-06-07 14:20:08.235642
684	rossfreedman@gmail.com	page_visit	mobile_team_schedule	\N	\N	166.199.152.86	2025-06-07 14:20:28.214353
685	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-07 14:22:10.198905
686	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	166.199.152.86	2025-06-07 14:22:20.114262
687	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-07 14:22:49.997468
688	rossfreedman@gmail.com	page_visit	mobile_team_schedule	\N	\N	166.199.152.86	2025-06-07 14:22:54.34964
689	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-07 14:22:56.493431
690	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-07 14:28:45.249327
691	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-07 14:29:19.865043
692	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	166.199.152.86	2025-06-07 14:29:44.517079
693	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-07 14:30:19.528777
694	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	166.199.152.86	2025-06-07 14:30:33.864315
695	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-07 14:31:11.420645
696	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	166.199.152.86	2025-06-07 14:31:23.316832
697	rossfreedman@gmail.com	page_visit	mobile_lineup_escrow	\N	Accessed mobile lineup escrow page	166.199.152.86	2025-06-07 14:31:34.231719
698	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 14:38:14.377783
699	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-07 14:38:19.450893
700	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-07 14:38:25.538662
701	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 14:38:29.38727
702	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 14:38:33.484496
703	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-07 14:38:37.139073
704	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 14:38:41.284997
705	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-07 14:38:48.816926
706	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-06-07 14:38:54.21481
707	rossfreedman@gmail.com	page_visit	mobile_lineup_escrow	\N	Accessed mobile lineup escrow page	73.22.198.26	2025-06-07 14:38:58.470742
708	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-07 14:39:05.14593
709	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 14:39:30.998608
710	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-07 14:39:35.081763
711	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 14:39:45.514734
712	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-07 14:39:48.310708
713	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 14:39:53.103376
714	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-07 14:39:57.111416
715	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 14:42:09.397563
716	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 14:42:13.725188
717	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 14:42:15.311543
718	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Charlie Kocmond	73.22.198.26	2025-06-07 14:42:19.20541
719	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 14:42:21.708161
720	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-07 14:42:26.626495
721	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-07 14:42:40.801876
722	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 14:47:21.132258
723	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-07 14:47:35.870538
724	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 14:47:37.569361
725	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 14:47:39.356494
726	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 14:47:52.061344
727	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 14:48:00.608731
728	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 14:48:09.622834
729	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 14:48:11.261732
730	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 14:48:22.502947
731	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-07 14:48:24.153555
732	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 14:48:28.132596
733	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 14:48:29.209979
734	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 14:48:40.518335
735	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 14:48:44.000103
736	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 14:48:45.827342
737	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 14:48:52.143594
738	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 15:03:47.72562
739	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-07 15:04:05.424046
740	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2024-10-01 to status 1	73.22.198.26	2025-06-07 15:04:31.45408
741	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-07 15:04:38.207534
742	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-03-15 to status 1	73.22.198.26	2025-06-07 15:04:42.64698
743	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-07 15:04:47.775887
744	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 15:04:57.180024
745	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 15:05:02.685835
746	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 15:05:16.585615
747	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 15:05:32.56002
748	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 15:05:39.979959
749	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 15:05:47.278413
750	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 15:06:01.033667
751	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 15:06:16.831279
752	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-07 15:06:28.998868
753	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 15:06:32.794869
754	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-07 15:06:38.755493
755	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-07 15:06:57.344413
756	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-07 15:07:02.642246
757	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 15:07:36.262133
758	rossfreedman@gmail.com	player_search	\N	\N	Searched for first name "Sridar", found 0 matches	73.22.198.26	2025-06-07 15:07:43.457419
759	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 15:07:43.47584
760	rossfreedman@gmail.com	player_search	\N	\N	Searched for first name "Mike", found 107 matches	73.22.198.26	2025-06-07 15:07:51.004316
761	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 15:07:51.021758
762	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "Bilwas", found 0 matches	73.22.198.26	2025-06-07 15:08:11.401661
763	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 15:08:11.42201
764	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 15:08:17.087511
765	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 15:08:17.773637
766	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 15:08:18.604144
767	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 15:08:26.694564
768	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 15:08:45.502774
769	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 15:08:50.610111
770	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-07 15:08:51.916958
771	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 15:08:58.298759
772	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 15:09:01.201639
773	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-07 15:09:12.058397
774	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-05-26 to status 1	73.22.198.26	2025-06-07 15:09:16.339218
775	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-05-29 to status 1	73.22.198.26	2025-06-07 15:09:18.15612
776	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-06-02 to status 1	73.22.198.26	2025-06-07 15:09:20.910411
777	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-06-09 to status 1	73.22.198.26	2025-06-07 15:09:36.803334
778	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-06-09 to status 2	73.22.198.26	2025-06-07 15:09:42.444762
779	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-06-16 to status 1	73.22.198.26	2025-06-07 15:09:46.295628
780	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-06-19 to status 1	73.22.198.26	2025-06-07 15:09:48.108916
781	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-06-23 to status 1	73.22.198.26	2025-06-07 15:09:49.429946
782	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-06-26 to status 1	73.22.198.26	2025-06-07 15:09:51.018666
783	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 15:09:55.956818
784	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-07 15:10:04.407528
925	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 21:51:44.836072
785	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-06-30 to status 1	73.22.198.26	2025-06-07 15:10:12.560189
786	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-07-07 to status 1	73.22.198.26	2025-06-07 15:10:14.804937
787	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-07-10 to status 1	73.22.198.26	2025-06-07 15:10:17.625394
788	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-07-14 to status 1	73.22.198.26	2025-06-07 15:10:20.917285
789	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-07-21 to status 1	73.22.198.26	2025-06-07 15:10:22.423107
790	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-07-24 to status 3	73.22.198.26	2025-06-07 15:10:25.981203
791	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-07-17 to status 2	73.22.198.26	2025-06-07 15:10:28.291103
792	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-07-24 to status 2	73.22.198.26	2025-06-07 15:10:29.674818
793	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-07-28 to status 1	73.22.198.26	2025-06-07 15:10:32.212894
794	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-07-28 to status 2	73.22.198.26	2025-06-07 15:10:33.783498
795	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-08-04 to status 2	73.22.198.26	2025-06-07 15:10:35.302014
796	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-07-31 to status 2	73.22.198.26	2025-06-07 15:10:39.672301
797	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-08-07 to status 2	73.22.198.26	2025-06-07 15:10:43.172972
798	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-08-07 to status 1	73.22.198.26	2025-06-07 15:10:45.441591
799	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-07 15:10:52.752878
800	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 15:10:56.518899
801	rossfreedman@gmail.com	player_search	\N	\N	Searched for first name "Ross", found 9 matches	73.22.198.26	2025-06-07 15:11:00.572954
802	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 15:11:00.599683
803	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Ross Freedman	73.22.198.26	2025-06-07 15:11:07.629325
804	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "Freed", found 2 matches	73.22.198.26	2025-06-07 15:11:24.888667
805	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 15:11:24.905304
806	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 15:11:31.181199
807	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 15:11:32.664257
808	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-07 15:11:37.485648
809	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-07 15:15:28.77828
810	disrael@aol.com	auth	\N	register	Registration successful. No Player ID match found	73.22.198.26	2025-06-07 15:16:35.170829
811	disrael@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 15:16:35.295363
812	disrael@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 15:16:38.628284
813	disrael@aol.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-07 15:16:42.45848
814	disrael@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 15:16:48.257656
815	disrael@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 15:16:51.992734
816	disrael@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 15:17:09.063986
817	disrael@aol.com	page_visit	mobile_lineup_escrow	\N	Accessed mobile lineup escrow page	73.22.198.26	2025-06-07 15:17:59.586588
818	disrael@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 15:18:01.50525
819	disrael@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 15:18:05.693508
820	disrael@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 15:18:51.186992
821	saktar@aol.com	auth	\N	register	Registration successful. Matched to Player ID: nndz-WkM2L3libnhndz09	73.22.198.26	2025-06-07 15:19:29.547329
822	saktar@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 15:19:29.802096
823	saktar@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 15:19:56.999835
824	saktar@aol.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-07 15:20:06.580508
825	saktar@aol.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-07 15:20:11.675084
826	saktar@aol.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-07 15:20:14.268866
827	saktar@aol.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-07 15:20:31.255075
828	saktar@aol.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-07 15:20:44.922358
829	saktar@aol.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-06-07 15:20:52.679704
830	saktar@aol.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-07 15:22:00.867476
831	Sinan Aktar	availability_update	mobile_availability	\N	Set availability for 2025-01-07 to status 1	73.22.198.26	2025-06-07 15:22:08.636607
832	saktar@aol.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-07 15:22:13.861798
833	saktar@aol.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-07 15:22:16.679556
834	saktar@aol.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-07 15:22:18.490133
835	saktar@aol.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 15:23:03.913068
836	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 17:37:25.431191
837	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-07 17:41:01.797853
838	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 17:41:01.872225
839	saktar@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 18:28:07.875726
840	saktar@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 18:28:07.889624
841	saktar@aol.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-07 18:28:09.991032
842	saktar@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 18:28:16.519069
843	saktar@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 18:28:18.031013
844	saktar@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 18:28:21.631914
845	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-07 18:28:29.701478
846	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 18:28:29.916103
847	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-07 18:28:33.642737
848	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-07 18:28:48.815354
849	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-07 18:28:51.798409
850	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 18:28:57.144613
851	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-07 18:29:04.197195
852	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-07 18:29:08.590726
853	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-06-07 18:29:12.331237
854	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-06-07 18:29:14.974035
855	rossfreedman@gmail.com	page_visit	mobile_team_schedule	\N	\N	73.22.198.26	2025-06-07 18:29:18.532478
856	rossfreedman@gmail.com	page_visit	mobile_team_schedule	\N	\N	73.22.198.26	2025-06-07 18:29:20.826899
857	rossfreedman@gmail.com	page_visit	mobile_team_schedule	\N	\N	73.22.198.26	2025-06-07 18:29:25.970344
858	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 18:29:30.198755
859	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 18:29:30.76357
860	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 18:29:36.093498
861	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "Wagner", found 5 matches	73.22.198.26	2025-06-07 18:29:40.323801
862	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 18:29:40.342637
863	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Brian Wagner	73.22.198.26	2025-06-07 18:29:47.070555
864	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Brian Wagner	73.22.198.26	2025-06-07 18:29:50.38951
865	rossfreedman@gmail.com	auth	\N	login	Login successful	98.46.111.71	2025-06-07 20:10:17.018777
866	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	98.46.111.71	2025-06-07 20:10:17.136434
867	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	98.46.111.71	2025-06-07 20:10:23.269834
868	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	98.46.111.71	2025-06-07 20:10:36.022829
869	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	98.46.111.71	2025-06-07 20:10:36.052799
870	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	98.46.111.71	2025-06-07 20:10:36.532194
871	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	98.46.111.71	2025-06-07 20:12:16.227182
872	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	98.46.111.71	2025-06-07 20:12:22.931354
873	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-02-22 to status 2	98.46.111.71	2025-06-07 20:12:32.32202
874	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-03-01 to status 1	98.46.111.71	2025-06-07 20:12:35.429473
875	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	98.46.111.71	2025-06-07 20:12:46.082937
876	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	98.46.111.71	2025-06-07 20:13:40.535179
877	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 21:46:01.208311
878	rossfreedman@gmail.com	page_visit	mobile_availability	\N	\N	73.22.198.26	2025-06-07 21:46:06.232342
879	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2024-09-24 to status 2	73.22.198.26	2025-06-07 21:46:15.086242
880	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2024-09-24 to status 1	73.22.198.26	2025-06-07 21:46:16.16708
881	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-07 21:46:21.02979
882	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-07 21:46:24.610589
883	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-07 21:46:26.831452
884	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 21:46:38.061678
885	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 21:46:56.122543
886	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 21:46:58.151048
887	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 21:47:06.080686
888	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 21:47:10.933743
889	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 21:47:15.903143
890	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 21:47:25.935118
891	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 21:47:34.600741
892	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 21:47:34.846441
893	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-07 21:47:48.304786
894	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-07 21:47:56.0163
895	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-07 21:47:59.36711
896	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 21:48:06.788197
897	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "Fox", found 0 matches	73.22.198.26	2025-06-07 21:48:15.829785
898	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 21:48:15.848735
899	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "Cone", found 0 matches	73.22.198.26	2025-06-07 21:48:27.709085
900	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 21:48:27.728705
901	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "Cond", found 1 matches	73.22.198.26	2025-06-07 21:48:32.39463
902	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 21:48:32.410304
903	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Jeffrey Condren	73.22.198.26	2025-06-07 21:48:36.68844
904	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "Fox", found 0 matches	73.22.198.26	2025-06-07 21:48:58.164426
905	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 21:48:58.180714
906	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 21:48:58.969604
907	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 21:49:00.633128
908	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-07 21:49:02.749299
909	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-07 21:49:11.266078
910	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 21:49:22.831236
911	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-07 21:49:40.335402
912	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-06-07 21:49:43.667243
913	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 21:49:50.382425
914	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 21:50:04.69968
915	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 21:50:10.196527
916	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Eli Strick	73.22.198.26	2025-06-07 21:50:26.500594
917	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-07 21:50:42.432926
918	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 21:51:02.489662
919	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 21:51:05.955246
920	rossfreedman@gmail.com	page_visit	mobile_practice_times	\N	\N	73.22.198.26	2025-06-07 21:51:17.028228
921	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 21:51:26.837716
922	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 21:51:29.040636
923	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Bob Crawford	73.22.198.26	2025-06-07 21:51:32.628955
924	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 21:51:41.219151
926	rossfreedman@gmail.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-07 21:51:53.82229
927	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-06-02 to status 2	73.22.198.26	2025-06-07 21:52:00.034633
928	Ross Freedman	availability_update	mobile_availability	\N	Set availability for 2025-06-02 to status 1	73.22.198.26	2025-06-07 21:52:02.295514
929	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-07 21:52:10.785347
930	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 21:52:18.799726
931	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 21:52:42.828191
932	rossfreedman@gmail.com	page_visit	mobile_reserve_court	\N	\N	73.22.198.26	2025-06-07 21:52:44.429124
933	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 21:52:46.956411
934	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-07 21:52:49.898113
935	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-07 21:52:52.497095
936	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-07 21:52:54.60233
937	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 21:52:58.606277
938	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "Condren", found 1 matches	73.22.198.26	2025-06-07 21:53:04.398431
939	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 21:53:04.420931
940	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Jeff Condren	73.22.198.26	2025-06-07 21:53:11.696315
941	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 21:53:28.499876
942	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 21:53:34.398862
943	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 21:53:40.051243
944	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Jack Fitzgibbons	73.22.198.26	2025-06-07 21:53:44.153264
945	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Paul Anderson	73.22.198.26	2025-06-07 21:53:47.938304
946	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Ned Kennedy Jr.	73.22.198.26	2025-06-07 21:53:54.062556
947	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Mark Donnelly	73.22.198.26	2025-06-07 21:54:07.362748
948	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 21:54:19.231042
949	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 21:54:20.455585
950	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-07 21:54:21.800691
951	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-07 21:54:35.808265
952	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 21:54:44.501949
953	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 21:55:11.310536
954	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 21:55:15.719411
955	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-07 21:55:18.201626
956	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-07 21:55:21.631447
957	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-07 21:55:23.35619
958	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 21:55:27.082832
959	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "Condren", found 1 matches	73.22.198.26	2025-06-07 21:55:32.433623
960	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 21:55:32.452655
961	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Jeffrey Condren	73.22.198.26	2025-06-07 21:55:35.208936
962	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 21:57:30.060371
963	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 21:57:31.26575
964	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 21:57:32.417152
965	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 21:57:36.02999
966	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 21:57:40.371199
967	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 21:57:43.242248
968	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Andrew Fluri	73.22.198.26	2025-06-07 21:57:50.1114
969	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Rodrigo Angel	73.22.198.26	2025-06-07 21:58:08.319105
970	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 21:58:11.512861
971	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 21:58:13.07374
972	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-07 21:58:17.831334
973	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 21:58:25.362251
974	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 21:58:29.129794
975	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "Wagner", found 4 matches	73.22.198.26	2025-06-07 21:58:34.494934
976	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 21:58:34.512351
977	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Brian Wagner	73.22.198.26	2025-06-07 21:58:39.894412
978	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 21:58:50.119099
979	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-07 22:00:28.130019
980	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-07 22:00:33.302266
981	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-07 22:03:47.825468
982	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:03:52.539856
983	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:03:53.660235
984	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:04:10.040401
985	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:04:11.520714
986	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-07 22:04:15.599247
987	rossfreedman@gmail.com	page_visit	mobile_lineup	\N	\N	73.22.198.26	2025-06-07 22:04:29.699041
988	rossfreedman@gmail.com	page_visit	mobile_lineup_escrow	\N	Accessed mobile lineup escrow page	73.22.198.26	2025-06-07 22:04:47.399919
989	rossfreedman@gmail.com	page_visit	mobile_practice_times	\N	\N	73.22.198.26	2025-06-07 22:04:50.207531
990	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-07 22:04:57.295907
991	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 22:04:59.897727
992	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-07 22:05:02.508922
993	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-07 22:05:05.499556
994	rossfreedman@gmail.com	page_visit	mobile_improve	\N	Accessed improve page	73.22.198.26	2025-06-07 22:05:09.242384
995	rossfreedman@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	73.22.198.26	2025-06-07 22:05:12.421945
996	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:05:40.245211
997	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 22:05:45.539434
998	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "Fox", found 4 matches	73.22.198.26	2025-06-07 22:05:55.721416
999	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 22:05:55.737363
1000	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Sam Fox	73.22.198.26	2025-06-07 22:06:02.062731
1001	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Doug Fox	73.22.198.26	2025-06-07 22:06:23.840009
1002	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-07 22:06:41.996264
1003	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:06:43.066028
1004	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-07 22:06:46.445178
1005	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:06:55.385829
1006	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:07:04.632241
1007	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 22:07:07.102704
1008	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:07:10.403882
1009	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-07 22:07:24.322681
1010	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:07:24.414512
1011	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:07:25.962824
1012	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:07:39.126439
1013	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:07:48.251503
1014	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:07:49.39985
1015	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 22:07:53.126006
1016	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-07 22:07:57.998689
1017	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-07 22:08:04.351712
1018	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-07 22:08:07.868004
1019	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-07 22:08:10.182254
1020	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:08:22.394331
1021	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:08:36.499162
1022	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:08:38.462075
1023	jeff@aol.com	auth	\N	register	Registration successful. No Player ID match found	73.22.198.26	2025-06-07 22:09:43.16748
1024	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:09:43.259648
1025	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:09:45.146808
1026	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:10:01.678233
1027	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:10:09.371896
1028	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:10:15.265643
1029	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:10:26.902546
1030	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:11:22.93978
1031	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 22:11:34.172351
1032	jeff@aol.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-07 22:11:37.328385
1033	jeff@aol.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-07 22:11:40.571014
1034	jeff@aol.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-07 22:11:42.515725
1035	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 22:11:44.717414
1036	jeff@aol.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-07 22:12:01.132635
1037	jeff@aol.com	page_visit	mobile_availability_calendar	\N	\N	73.22.198.26	2025-06-07 22:12:04.632672
1038	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:12:15.569052
1039	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:12:24.403557
1040	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:12:28.375352
1041	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:12:29.285869
1042	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:12:52.18401
1043	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:12:55.82981
1044	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:12:56.403093
1045	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 22:12:58.025641
1046	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:13:02.496479
1047	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:13:10.005996
1048	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:13:13.899307
1049	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 22:13:16.499866
1050	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:13:26.899792
1051	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:13:28.016705
1052	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:13:41.334063
1053	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:13:43.925687
1054	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 22:13:46.076791
1055	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:13:48.509589
1056	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:13:49.840446
1057	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:13:59.559875
1058	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:14:00.626057
1059	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-07 22:14:02.795252
1060	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:14:10.901924
1061	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:14:11.894421
1062	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-07 22:14:12.473341
1063	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-07 22:14:25.604728
1064	jeff@aol.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-07 22:35:27.428723
1065	jeff@aol.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-08 06:24:56.626037
1066	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 07:10:56.219846
1067	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 07:11:04.751672
1068	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "freedman", found 2 matches	73.22.198.26	2025-06-08 07:11:08.001999
1069	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 07:11:08.024159
1070	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "wagner", found 4 matches	73.22.198.26	2025-06-08 07:11:12.734228
1071	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 07:11:12.750281
1072	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Brian Wagner	73.22.198.26	2025-06-08 07:11:14.506976
1073	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 07:11:36.549885
1074	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-08 07:11:40.137246
1075	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 07:11:40.23564
1076	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 07:12:01.667363
1077	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "wagner", found 1 matches	73.22.198.26	2025-06-08 07:12:03.449904
1078	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 07:12:03.467533
1079	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "wagner", found 1 matches	73.22.198.26	2025-06-08 07:12:22.477077
1080	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 07:12:22.494184
1081	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 07:12:25.472379
1082	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 07:12:26.408783
1083	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 07:12:49.326024
1084	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 07:12:53.205392
1085	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 07:13:04.081948
1086	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 07:13:07.596112
1087	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 07:13:09.260096
1088	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 07:13:25.797994
1089	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 07:13:28.095373
1090	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 07:13:31.196433
1091	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "wagner", found 4 matches	73.22.198.26	2025-06-08 07:13:34.595871
1092	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 07:13:34.618713
1093	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Brian Wagner	73.22.198.26	2025-06-08 07:13:48.491331
1094	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 07:16:19.407637
1095	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 07:16:19.786669
1096	rossfreedman@gmail.com	page_visit	mobile_find_subs	\N	\N	73.22.198.26	2025-06-08 07:16:22.295666
1097	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 07:20:04.787628
1098	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "wagner", found 4 matches	73.22.198.26	2025-06-08 07:20:06.613475
1099	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 07:20:06.629795
1100	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Brian Wagner	73.22.198.26	2025-06-08 07:20:08.492479
1101	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 07:20:13.129017
1102	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 07:20:15.914599
1103	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 07:20:19.229569
1104	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "wagner", found 4 matches	73.22.198.26	2025-06-08 07:20:21.445566
1105	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 07:20:21.464942
1106	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Brian Wagner	73.22.198.26	2025-06-08 07:20:23.439956
1107	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Brian Wagner	73.22.198.26	2025-06-08 07:20:31.14736
1108	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 07:20:35.010524
1109	rossfreedman@gmail.com	auth	\N	login	Login successful	73.22.198.26	2025-06-08 07:20:38.654774
1110	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 07:20:38.875418
1111	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 07:20:41.312935
1112	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "wagner", found 4 matches	73.22.198.26	2025-06-08 07:20:43.627781
1113	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 07:20:43.647482
1114	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Brian Wagner	73.22.198.26	2025-06-08 07:20:45.524227
1115	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Brian Wagner	73.22.198.26	2025-06-08 07:21:17.813744
1116	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 07:21:18.960197
1117	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 07:34:15.647465
1118	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 07:34:17.174037
1119	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 07:57:22.191709
1120	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-08 08:01:57.625068
1121	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-08 08:02:01.039802
1122	rossfreedman@gmail.com	page_visit	mobile_teams_players	\N	\N	73.22.198.26	2025-06-08 08:04:30.112794
1123	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 08:27:37.295225
1124	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 08:27:44.094604
1125	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 08:27:48.596737
1126	jeff@aol.com	page_visit	mobile_reserve_court	\N	\N	73.22.198.26	2025-06-08 08:27:51.595106
1127	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 08:28:02.303188
1128	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 08:28:11.142773
1129	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 08:28:14.521441
1130	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 08:28:15.786362
1131	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 08:28:21.473014
1132	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 08:28:23.132815
1133	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 08:28:26.526949
1134	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 08:29:10.86347
1135	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 08:29:13.831247
1136	jeff@aol.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 08:29:19.427838
1137	jeff@aol.com	player_search	\N	\N	Searched for last name "Cond", found 1 matches	73.22.198.26	2025-06-08 08:29:23.643669
1138	jeff@aol.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 08:29:23.659193
1139	jeff@aol.com	page_visit	mobile_player_detail	\N	Viewed player Jeff Condren	73.22.198.26	2025-06-08 08:29:25.549167
1140	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 08:29:28.717732
1141	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 08:29:32.287994
1142	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 08:29:37.409533
1143	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 08:29:41.840125
1144	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 08:29:43.28628
1145	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 08:29:54.022836
1146	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 08:30:00.273574
1147	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 08:30:02.435168
1148	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 08:30:54.486853
1149	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 12:32:37.351224
1150	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 12:32:40.939211
1151	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:32:42.575815
1152	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:34:05.403252
1153	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 12:34:06.218481
1154	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:34:14.283929
1155	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 12:34:20.513813
1156	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 12:34:25.69933
1157	rossfreedman@gmail.com	player_search	\N	\N	Searched for last name "condren", found 1 matches	73.22.198.26	2025-06-08 12:34:29.13656
1158	rossfreedman@gmail.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 12:34:29.151233
1159	rossfreedman@gmail.com	page_visit	mobile_player_detail	\N	Viewed player Jeffrey Condren	73.22.198.26	2025-06-08 12:34:30.583682
1160	jeff@aol.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-08 12:34:53.435137
1161	jeff@aol.com	page_visit	mobile_my_club	\N	\N	73.22.198.26	2025-06-08 12:34:53.595726
1162	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:34:55.52075
1163	jeff@aol.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 12:34:57.858283
1164	jeff@aol.com	player_search	\N	\N	Searched for last name "Condren", found 1 matches	73.22.198.26	2025-06-08 12:35:03.54554
1165	jeff@aol.com	page_visit	mobile_player_search	\N	\N	73.22.198.26	2025-06-08 12:35:03.559793
1166	jeff@aol.com	page_visit	mobile_player_detail	\N	Viewed player Jeff Condren	73.22.198.26	2025-06-08 12:35:06.444378
1167	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:35:08.59915
1168	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 12:35:16.694307
1169	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:35:21.195282
1170	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 12:35:22.605255
1171	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:35:32.00003
1172	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 12:35:33.926831
1173	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:35:41.196378
1174	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:35:41.752671
1175	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 12:35:44.192863
1176	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 12:35:49.824275
1177	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:35:54.593332
1178	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 12:35:56.03802
1179	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:36:02.578674
1180	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:36:06.461599
1181	jeff@aol.com	auth	\N	login	Login successful	73.22.198.26	2025-06-08 12:36:29.257754
1182	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:36:29.33023
1183	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 12:36:33.335879
1184	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:36:40.852346
1185	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 12:36:41.500631
1186	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 12:37:11.488877
1187	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:37:29.322276
1188	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 12:37:31.260596
1189	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:42:04.008521
1190	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 12:42:05.123787
1191	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 12:42:11.987169
1192	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:42:12.319758
1193	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 12:42:14.071383
1194	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 12:42:31.635401
1195	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 12:43:28.870687
1196	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 12:46:35.651597
1197	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 12:47:09.671631
1198	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:47:17.784609
1199	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 12:47:20.882036
1200	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:48:08.185549
1201	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 12:48:12.202341
1202	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:48:15.286442
1203	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 12:48:15.996617
1204	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 12:48:44.297253
1205	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 12:48:45.302095
1206	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 12:59:58.084422
1207	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 13:03:44.367855
1208	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 13:09:28.459807
1209	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 13:09:40.927606
1210	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 13:09:44.491659
1211	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 13:09:45.833905
1212	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 13:09:51.985703
1213	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 13:10:01.421168
1214	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 13:10:03.73643
1215	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 13:10:05.427323
1216	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 13:10:10.357246
1217	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 13:10:12.75814
1218	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 13:10:26.097975
1219	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 13:10:33.052236
1220	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 13:10:34.945015
1221	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 13:10:38.267207
1222	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 13:10:45.307209
1223	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 13:10:47.202257
1224	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 13:10:47.918333
1225	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 13:11:00.809145
1226	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 13:11:03.057702
1227	jeff@aol.com	page_visit	mobile_reserve_court	\N	\N	73.22.198.26	2025-06-08 13:11:03.947795
1228	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 13:11:04.75764
1229	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 13:11:06.010982
1230	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 13:11:07.99413
1231	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-08 13:11:09.60967
1232	jeff@aol.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-08 13:11:10.862645
1233	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 13:11:11.562956
1234	jeff@aol.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-08 13:11:18.723556
1235	jeff@aol.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 13:26:16.375167
1236	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	166.199.152.86	2025-06-08 13:26:19.396022
1237	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	166.199.152.86	2025-06-08 13:26:23.494016
1238	jeff@aol.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 13:26:29.94259
1239	jeff@aol.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-08 13:26:31.035497
1240	jeff@aol.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-08 13:26:35.513473
1241	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	166.199.152.86	2025-06-08 13:26:41.02961
1242	jeff@aol.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 13:26:48.334818
1243	jeff@aol.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-08 13:26:49.513465
1244	jeff@aol.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-08 13:27:06.247179
1245	jeff@aol.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 13:27:08.614564
1246	jeff@aol.com	page_visit	mobile_analyze_me	\N	\N	166.199.152.86	2025-06-08 13:27:11.412971
1247	jeff@aol.com	page_visit	mobile_availability	\N	\N	166.199.152.86	2025-06-08 13:27:23.234829
1248	Jeffrey Condren	availability_update	mobile_availability	\N	Set availability for 2025-05-29 to status 2	166.199.152.86	2025-06-08 13:27:28.141447
1249	jeff@aol.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-08 13:27:36.516145
1250	jeff@aol.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-08 13:27:42.688785
1251	jeff@aol.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 13:27:44.309927
1252	jeff@aol.com	page_visit	mobile_availability	\N	\N	166.199.152.86	2025-06-08 13:27:48.681854
1253	jeff@aol.com	page_visit	mobile_all_team_availability	\N	\N	166.199.152.86	2025-06-08 13:27:56.742933
1254	jeff@aol.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 13:28:00.864194
1255	jeff@aol.com	page_visit	mobile_availability_calendar	\N	\N	166.199.152.86	2025-06-08 13:28:05.502415
1256	Jeffrey Condren	availability_update	mobile_availability	\N	Set availability for 2025-06-09 to status 1	166.199.152.86	2025-06-08 13:28:08.014003
1257	jeff@aol.com	page_visit	mobile_all_team_availability	\N	\N	166.199.152.86	2025-06-08 13:28:10.551569
1258	jeff@aol.com	page_visit	mobile_all_team_availability	\N	\N	166.199.152.86	2025-06-08 13:28:20.065572
1259	Jeffrey Condren	availability_update	mobile_availability	\N	Set availability for 2025-06-02 to status 1	166.199.152.86	2025-06-08 13:28:25.642096
1260	Jeffrey Condren	availability_update	mobile_availability	\N	Set availability for 2025-06-16 to status 2	166.199.152.86	2025-06-08 13:28:28.1037
1261	Jeffrey Condren	availability_update	mobile_availability	\N	Set availability for 2025-06-30 to status 1	166.199.152.86	2025-06-08 13:28:42.915972
1262	jeff@aol.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 13:28:45.320783
1263	jeff@aol.com	page_visit	mobile_find_people_to_play	\N	\N	166.199.152.86	2025-06-08 13:28:47.397896
1264	jeff@aol.com	page_visit	mobile_my_team	\N	\N	166.199.152.86	2025-06-08 13:28:53.59857
1265	jeff@aol.com	page_visit	mobile_my_series	\N	\N	166.199.152.86	2025-06-08 13:29:01.299796
1266	jeff@aol.com	page_visit	mobile_player_search	\N	\N	166.199.152.86	2025-06-08 13:29:02.965527
1267	jeff@aol.com	player_search	\N	\N	Searched for first name "Sri", found 0 matches	166.199.152.86	2025-06-08 13:29:09.041421
1268	jeff@aol.com	page_visit	mobile_player_search	\N	\N	166.199.152.86	2025-06-08 13:29:09.060036
1269	jeff@aol.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 13:29:11.722697
1270	jeff@aol.com	page_visit	mobile_teams_players	\N	\N	166.199.152.86	2025-06-08 13:29:18.065689
1271	jeff@aol.com	page_visit	mobile_teams_players	\N	\N	166.199.152.86	2025-06-08 13:29:23.650788
1272	jeff@aol.com	page_visit	mobile_player_detail	\N	Viewed player Sridar Komar	166.199.152.86	2025-06-08 13:29:31.184906
1273	jeff@aol.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 13:29:37.433661
1274	jeff@aol.com	page_visit	mobile_player_search	\N	\N	166.199.152.86	2025-06-08 13:29:40.154602
1275	jeff@aol.com	player_search	\N	\N	Searched for first name "Sridar", found 1 matches	166.199.152.86	2025-06-08 13:29:43.845376
1276	jeff@aol.com	page_visit	mobile_player_search	\N	\N	166.199.152.86	2025-06-08 13:29:43.871155
1277	jeff@aol.com	player_search	\N	\N	Searched for first name "Sr", found 0 matches	166.199.152.86	2025-06-08 13:29:48.38097
1278	jeff@aol.com	page_visit	mobile_player_search	\N	\N	166.199.152.86	2025-06-08 13:29:48.406825
1279	jeff@aol.com	player_search	\N	\N	Searched for first name "Srid", found 1 matches	166.199.152.86	2025-06-08 13:29:54.835852
1280	jeff@aol.com	page_visit	mobile_player_search	\N	\N	166.199.152.86	2025-06-08 13:29:54.854064
1281	jeff@aol.com	player_search	\N	\N	Searched for first name "Sridar", found 1 matches	166.199.152.86	2025-06-08 13:30:02.297473
1282	jeff@aol.com	page_visit	mobile_player_search	\N	\N	166.199.152.86	2025-06-08 13:30:02.315354
1283	jeff@aol.com	page_visit	mobile_player_detail	\N	Viewed player Sridar Komar	166.199.152.86	2025-06-08 13:30:05.728867
1284	jeff@aol.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 13:30:12.674206
1285	jeff@aol.com	page_visit	mobile_my_club	\N	\N	166.199.152.86	2025-06-08 13:30:16.049571
1286	jeff@aol.com	page_visit	mobile_find_subs	\N	\N	166.199.152.86	2025-06-08 13:30:37.422258
1287	jeff@aol.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 13:41:26.478794
1288	jeff@aol.com	page_visit	mobile_find_people_to_play	\N	\N	166.199.152.86	2025-06-08 13:42:10.709713
1289	jeff@aol.com	page_visit	mobile_find_people_to_play	\N	\N	166.199.152.86	2025-06-08 13:58:37.009284
1290	jeff@aol.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 13:58:38.625115
1291	dlyden@gmail.com	auth	\N	register	Registration successful. Matched to Player ID: nndz-WkMrK3didjlqQT09	166.199.152.86	2025-06-08 13:59:41.741506
1292	dlyden@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 13:59:41.990096
1293	dlyden@gmail.com	page_visit	mobile_analyze_me	\N	\N	166.199.152.86	2025-06-08 13:59:47.369099
1294	dlyden@gmail.com	page_visit	mobile_my_team	\N	\N	166.199.152.86	2025-06-08 13:59:56.651604
1295	dlyden@gmail.com	page_visit	mobile_my_team	\N	\N	166.199.152.86	2025-06-08 13:59:56.767361
1296	dlyden@gmail.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-08 14:00:04.646785
1297	dlyden@gmail.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-08 14:00:13.723019
1298	dlyden@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 14:00:15.63086
1299	dlyden@gmail.com	page_visit	mobile_analyze_me	\N	\N	166.199.152.86	2025-06-08 14:00:17.925216
1300	dlyden@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 14:00:19.478831
1301	dlyden@gmail.com	page_visit	mobile_find_people_to_play	\N	\N	166.199.152.86	2025-06-08 14:00:21.901209
1302	dlyden@gmail.com	page_visit	mobile_my_club	\N	\N	166.199.152.86	2025-06-08 14:00:27.79676
1303	dlyden@gmail.com	page_visit	mobile_my_series	\N	\N	166.199.152.86	2025-06-08 14:00:29.779233
1304	dlyden@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 14:00:35.82905
1305	dlyden@gmail.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-08 14:00:39.342288
1306	dlyden@gmail.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-08 14:00:46.373052
1307	dlyden@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 14:00:47.659002
1308	dlyden@gmail.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-08 14:04:13.282895
1309	dlyden@gmail.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-08 14:04:22.884107
1310	dlyden@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 14:04:24.139998
1311	dlyden@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 14:04:24.59878
1312	dlyden@gmail.com	page_visit	mobile_analyze_me	\N	\N	166.199.152.86	2025-06-08 14:04:27.341412
1313	dlyden@gmail.com	page_visit	mobile_analyze_me	\N	\N	166.199.152.86	2025-06-08 14:04:34.022689
1314	dlyden@gmail.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-08 14:04:41.05639
1315	dlyden@gmail.com	page_visit	mobile_settings	\N	\N	166.199.152.86	2025-06-08 14:04:54.235947
1316	dlyden@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 14:04:56.112737
1317	dlyden@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 14:04:56.646186
1318	dlyden@gmail.com	page_visit	mobile_analyze_me	\N	\N	166.199.152.86	2025-06-08 14:05:02.495701
1319	dlyden@gmail.com	page_visit	mobile_my_team	\N	\N	166.199.152.86	2025-06-08 14:05:05.921119
1320	dlyden@gmail.com	page_visit	mobile_find_subs	\N	\N	166.199.152.86	2025-06-08 14:05:11.302941
1321	dlyden@gmail.com	page_visit	mobile_lineup_escrow	\N	Accessed mobile lineup escrow page	166.199.152.86	2025-06-08 14:05:19.645276
1322	dlyden@gmail.com	page_visit	mobile_lineup	\N	\N	166.199.152.86	2025-06-08 14:05:21.015069
1323	dlyden@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 15:11:04.689366
1324	dlyden@gmail.com	page_visit	mobile_home	\N	\N	166.199.152.86	2025-06-08 15:11:18.995254
1325	dlyden@gmail.com	page_visit	mobile_home	\N	\N	24.142.147.68	2025-06-08 17:44:12.097464
1326	rick@aol.com	auth	\N	register	Registration successful. No Player ID match found	24.142.147.68	2025-06-08 17:45:00.713157
1327	rick@aol.com	page_visit	mobile_home	\N	\N	24.142.147.68	2025-06-08 17:45:00.770503
1328	rick@aol.com	page_visit	mobile_analyze_me	\N	\N	24.142.147.68	2025-06-08 17:45:16.15587
1329	rick@aol.com	page_visit	mobile_my_team	\N	\N	24.142.147.68	2025-06-08 17:45:27.216911
1330	rick@aol.com	page_visit	mobile_my_series	\N	\N	24.142.147.68	2025-06-08 17:45:29.649346
1331	rick@aol.com	page_visit	mobile_find_subs	\N	\N	24.142.147.68	2025-06-08 17:45:32.65557
1332	rick@aol.com	page_visit	mobile_find_subs	\N	\N	24.142.147.68	2025-06-08 17:45:36.542633
1333	rick@aol.com	page_visit	mobile_find_subs	\N	\N	24.142.147.68	2025-06-08 17:45:36.59394
1334	rick@aol.com	page_visit	mobile_player_search	\N	\N	24.142.147.68	2025-06-08 17:45:39.420216
1335	rick@aol.com	player_search	\N	\N	Searched for first name "Rick", found 34 matches	24.142.147.68	2025-06-08 17:45:44.891543
1336	rick@aol.com	page_visit	mobile_player_search	\N	\N	24.142.147.68	2025-06-08 17:45:44.909251
1337	rick@aol.com	page_visit	mobile_player_detail	\N	Viewed player Rick Lapiana	24.142.147.68	2025-06-08 17:45:59.716718
1338	rick@aol.com	page_visit	mobile_home	\N	\N	24.142.147.68	2025-06-08 17:46:02.231959
1339	rick@aol.com	page_visit	mobile_settings	\N	\N	24.142.147.68	2025-06-08 17:46:04.704908
1340	rick@aol.com	page_visit	mobile_settings	\N	\N	24.142.147.68	2025-06-08 17:46:13.0398
1341	rick@aol.com	page_visit	mobile_home	\N	\N	24.142.147.68	2025-06-08 17:46:14.674043
1342	rick@aol.com	page_visit	mobile_analyze_me	\N	\N	24.142.147.68	2025-06-08 17:46:18.503901
1343	rick@aol.com	page_visit	mobile_home	\N	\N	166.199.98.89	2025-06-08 17:59:10.654004
1344	rick@aol.com	page_visit	mobile_availability	\N	\N	166.199.98.89	2025-06-08 17:59:14.544977
1345	Rick Lapiana	availability_update	mobile_availability	\N	Set availability for 2024-09-25 to status 1	166.199.98.89	2025-06-08 17:59:16.895741
1346	rick@aol.com	page_visit	mobile_teams_players	\N	\N	166.199.98.89	2025-06-08 17:59:20.204167
1347	rick@aol.com	page_visit	mobile_teams_players	\N	\N	166.199.98.89	2025-06-08 17:59:22.504958
1348	rick@aol.com	page_visit	mobile_player_detail	\N	Viewed player Brian Mickey	166.199.98.89	2025-06-08 17:59:25.885328
1349	rick@aol.com	page_visit	mobile_home	\N	\N	166.199.98.89	2025-06-08 17:59:32.940874
1350	rick@aol.com	page_visit	mobile_improve	\N	Accessed improve page	166.199.98.89	2025-06-08 17:59:35.335572
1351	rick@aol.com	page_visit	mobile_my_club	\N	\N	166.199.98.89	2025-06-08 17:59:50.818779
1352	rick@aol.com	page_visit	mobile_my_series	\N	\N	166.199.98.89	2025-06-08 17:59:53.24775
1353	rick@aol.com	page_visit	mobile_find_subs	\N	\N	166.199.98.89	2025-06-08 18:00:01.053899
1354	rick@aol.com	page_visit	mobile_lineup	\N	\N	166.199.98.89	2025-06-08 18:00:08.153378
1355	rick@aol.com	page_visit	mobile_home	\N	\N	166.199.98.89	2025-06-08 18:00:23.24014
1356	rick@aol.com	page_visit	mobile_find_subs	\N	\N	166.199.98.89	2025-06-08 18:00:45.062785
1357	rick@aol.com	page_visit	mobile_find_people_to_play	\N	\N	166.199.98.89	2025-06-08 18:00:52.67917
1358	rick@aol.com	page_visit	mobile_find_people_to_play	\N	\N	166.199.98.89	2025-06-08 18:02:03.619951
1359	rick@aol.com	page_visit	mobile_home	\N	\N	166.199.98.89	2025-06-08 18:02:18.713389
1360	rick@aol.com	page_visit	mobile_player_search	\N	\N	166.199.98.89	2025-06-08 18:02:23.525141
1361	rick@aol.com	player_search	\N	\N	Searched for first name "Ross", found 10 matches	166.199.98.89	2025-06-08 18:02:31.690308
1362	rick@aol.com	page_visit	mobile_player_search	\N	\N	166.199.98.89	2025-06-08 18:02:31.710188
1363	rick@aol.com	page_visit	mobile_find_people_to_play	\N	\N	166.199.98.89	2025-06-08 18:02:47.302392
1364	rick@aol.com	page_visit	mobile_find_people_to_play	\N	\N	166.199.98.89	2025-06-08 18:03:24.635388
1365	rick@aol.com	page_visit	mobile_find_people_to_play	\N	\N	166.199.98.89	2025-06-08 18:11:42.944017
1366	rick@aol.com	page_visit	mobile_find_people_to_play	\N	\N	166.199.98.89	2025-06-08 18:56:19.757941
1367	jeff@aol.com	page_visit	mobile_home	\N	\N	198.30.200.124	2025-06-08 21:13:42.058096
1368	rossfreedman@gmail.com	auth	\N	login	Login successful	198.30.200.124	2025-06-08 21:13:49.97078
1369	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	198.30.200.124	2025-06-08 21:13:50.112726
1370	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	198.30.200.124	2025-06-08 21:13:53.910556
1371	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	198.30.200.124	2025-06-08 21:13:59.783388
1372	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	198.30.200.124	2025-06-08 21:14:10.451069
1373	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	198.30.200.124	2025-06-08 21:14:14.595042
1374	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	198.30.200.124	2025-06-08 21:14:16.058498
1375	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	198.30.200.124	2025-06-08 21:16:53.211431
1376	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	198.30.200.124	2025-06-08 21:17:07.110885
1377	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	198.30.200.124	2025-06-08 21:17:08.871661
1378	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	198.30.200.124	2025-06-08 21:37:37.409278
1379	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	198.30.200.124	2025-06-08 21:37:40.429149
1380	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	198.30.200.124	2025-06-08 21:38:03.430337
1381	rossfreedman@gmail.com	page_visit	mobile_my_club	\N	\N	198.30.200.124	2025-06-08 21:38:06.130619
1382	rick@aol.com	page_visit	mobile_home	\N	\N	198.30.200.102	2025-06-09 05:11:43.353261
1383	rossfreedman@gmail.com	auth	\N	login	Login successful	24.142.147.68	2025-06-10 06:34:17.12636
1384	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	24.142.147.68	2025-06-10 06:34:17.39149
1385	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	24.142.147.68	2025-06-10 06:34:25.820144
1386	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	24.142.147.68	2025-06-10 06:34:36.426958
1387	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	24.142.147.68	2025-06-10 06:34:36.715992
1388	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	24.142.147.68	2025-06-10 06:34:38.360983
1389	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-10 13:37:32.501151
1390	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-10 13:37:34.349335
1391	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-10 13:38:28.286648
1392	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-10 13:38:31.064528
1393	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-10 13:38:42.543504
1394	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-10 13:38:47.662232
1395	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-10 13:38:49.350027
1396	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-10 13:58:19.637467
1397	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-10 13:58:21.930831
1398	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-10 18:31:05.796153
1399	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-10 18:31:07.606355
1400	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-10 18:31:13.696306
1401	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-10 18:31:14.117943
1402	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-10 18:31:15.851442
1403	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-10 18:35:04.34123
1404	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-10 18:35:05.506576
1405	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-10 18:35:07.917812
1406	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-10 18:36:29.149453
1407	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-10 19:27:18.722365
1408	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-10 19:27:19.665105
1409	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-10 19:36:40.436433
1410	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-10 19:36:42.676363
1411	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-10 19:39:49.800535
1412	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-10 19:39:49.817911
1413	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-10 19:39:50.729772
1414	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-10 19:52:50.535222
1415	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-10 19:52:52.407591
1416	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-10 19:55:40.238604
1417	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-10 20:18:59.520469
1418	rossfreedman@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-11 07:52:09.479587
1419	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-11 08:09:30.318678
1420	rossfreedman@gmail.com	page_visit	mobile_settings	\N	\N	73.22.198.26	2025-06-11 08:09:31.025145
1421	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-11 08:42:46.096494
1422	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-11 08:42:48.412567
1423	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-11 08:42:51.783415
1424	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-11 11:08:05.778509
1425	rossfreedman@gmail.com	page_visit	mobile_my_team	\N	\N	73.22.198.26	2025-06-11 11:08:05.930418
1426	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-11 14:31:59.403625
1427	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-11 14:32:01.709334
1428	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-11 14:32:23.189789
1429	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-11 14:32:33.543259
1430	rossfreedman@gmail.com	page_visit	mobile_my_series	\N	\N	73.22.198.26	2025-06-11 14:33:00.729092
1431	rossfreedman@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-11 14:33:34.040025
1432	brian@gmail.com	auth	\N	register	Registration successful. Matched to Player ID: nndz-WkNPd3g3citnQT09	73.22.198.26	2025-06-11 14:34:18.056764
1433	brian@gmail.com	page_visit	mobile_home	\N	\N	73.22.198.26	2025-06-11 14:34:18.190934
1434	brian@gmail.com	page_visit	mobile_analyze_me	\N	\N	73.22.198.26	2025-06-11 14:34:21.371104
\.


--
-- Data for Name: user_instructions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.user_instructions (id, user_email, instruction, created_at, updated_at, team_id, is_active) FROM stdin;
2	rossfreedman@gmail.com	test	2025-06-06 11:04:04.817139	2025-06-06 11:04:04.817139	\N	f
3	saktar@aol.com	Sinan and Marcus should play court 2	2025-06-07 15:21:15.991773	2025-06-07 15:21:15.991773	\N	t
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, email, password_hash, first_name, last_name, club_id, series_id, is_admin, created_at, club_automation_password, last_login, tenniscores_player_id, league_id) FROM stdin;
4	disrael@aol.com	pbkdf2:sha256:1000000$kod3u6OjXdP9TIBY$958ab2811bcbfb143a1e2add02cb84ce6b4360b1f5e223a6ddfe17cf172b478d	David	Israel	16	25	f	2025-06-07 15:16:35.135832	\N	\N	\N	1
5	saktar@aol.com	pbkdf2:sha256:1000000$27EpGzn1Is5jobT0$bd0d437d61b51714d4a9d4a3bb5ee7e0a6e290096b120a0e5a0ff3df94398a22	Sinan	Aktar	5	22	f	2025-06-07 15:19:29.504154	\N	\N	nndz-WkM2L3libnhndz09	1
7	rossfreedman@gmail.com	pbkdf2:sha256:1000000$fsxkBUxUvatei6gz$322d074c5e8035fb7688a0a53cbc0a6aeba587a3ad9eb066b70372d29554166c	Ross	Freedman	1	22	f	2025-05-18 11:31:24.509828	test	2025-05-23 18:37:14.903289	nndz-WkMrK3didjlnUT09	1
1	darenberg@gmail.com	pbkdf2:sha256:1000000$4wfsAeM7qDevPNLm$7058b35e516486f948c9dec147cb4e8ef33ab11ac151355ef611e4ec95a48a1f	Dave	Arenberg	1	19	f	2025-06-03 20:55:47.809125		\N	APTA_4813F614	1
12	jmday02@gmail.com	pbkdf2:sha256:1000000$29SXeT7Mu6c4CWjI$15bf358d21f287cdc9bd183921503e25ca60f7a7a26f6ebab0d7611f6e86e4c6	Jeff	Day	1	33	f	2025-05-25 15:34:33.157785	\N	\N	APTA_98CC47D8	1
11	scottosterman@yahoo.com	pbkdf2:sha256:1000000$rbXHTZNMIH6Xf4fD$f3d42e986dca3df7f0f92444eb255fcbda9b7d6a4686aae47a72895620a40337	Scott	Osterman	1	38	f	2025-05-24 22:56:14.501838	\N	\N	APTA_7DE188AF	1
13	petewahlstom@hotmail.com	pbkdf2:sha256:1000000$0NUTGJ1GINscFbOp$47dc82287f424a1a77ca5f1e31e2ba17ec67368180584bad9043786a2a1196a8	Pete	Wahlstrom	35	9	f	2025-05-26 00:24:58.735937	\N	\N	APTA_D4AB0B80	1
2	afranger@gmail.com	pbkdf2:sha256:1000000$Qgh0N6HIBS9gcPtl$b7bd7dbe6f6d1f604c4218af7f7247056e0c77b3e2b69446199dbb0f384b73f3	Andrew	Franger	1	22	f	2025-06-04 08:39:38.227617	\N	\N	APTA_DE52ECF6	1
3	bfox@aol.com	pbkdf2:sha256:1000000$M4FBqQBSDkvjX0xs$83512357eb11fcd8901e677254a5b562f0b614bbab79da50c844ca7e5b7f7dd4	Brian	Fox	1	6	f	2025-06-06 11:15:07.160368		\N	\N	1
10	brian@gmail.com	pbkdf2:sha256:1000000$sujpz4DHYz8V02Ea$60a5b7b955396c0427878626f34c6a80dc9572bf3351ead5d46975344d78fcfe	Brian	Fox	1	22	f	2025-06-11 14:34:18.014234	\N	\N	nndz-WkNPd3g3citnQT09	1
6	jeff@aol.com	pbkdf2:sha256:1000000$JpYeb7wwwXrEMB9F$2cc0f33b19212ef4fb73df3ad49bde68f57f2cf22b0681468df3960074a10a29	Jeffrey	Condren	1	114	f	2025-06-07 22:09:43.127876		\N	nndz-WkMrOXliejhoZz09	3
8	dlyden@gmail.com	pbkdf2:sha256:1000000$QBvJRu5yiVdPCrkY$4d78868b42e192ce14b5dd3178d299573019b01b83d20f2234aa1c57426bcb86	Daniel	Lyden	1	27	f	2025-06-08 13:59:41.704929		\N	nndz-WkMrK3didjlqQT09	1
9	rick@aol.com	pbkdf2:sha256:1000000$lrJ2PcT7xqt6P61C$313bc3c3bbb448c0c72dd5548469f3dd4939cf75cee52b4247526c4f5e7bc12b	Rick	Lapiana	1	15	f	2025-06-08 17:45:00.679693		\N	nndz-WkNPd3g3citodz09	1
\.


--
-- Name: club_leagues_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.club_leagues_id_seq', 960, true);


--
-- Name: clubs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.clubs_id_seq', 1, false);


--
-- Name: leagues_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.leagues_id_seq', 45, true);


--
-- Name: player_availability_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.player_availability_id_seq', 140, true);


--
-- Name: series_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.series_id_seq', 1, true);


--
-- Name: series_leagues_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.series_leagues_id_seq', 162, true);


--
-- Name: user_activity_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.user_activity_logs_id_seq', 1434, true);


--
-- Name: user_instructions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.user_instructions_id_seq', 3, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.users_id_seq', 10, true);


--
-- Name: alembic_version alembic_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkey PRIMARY KEY (version_num);


--
-- Name: club_leagues club_leagues_club_id_league_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_leagues
    ADD CONSTRAINT club_leagues_club_id_league_id_key UNIQUE (club_id, league_id);


--
-- Name: club_leagues club_leagues_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_leagues
    ADD CONSTRAINT club_leagues_pkey PRIMARY KEY (id);


--
-- Name: clubs clubs_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clubs
    ADD CONSTRAINT clubs_name_key UNIQUE (name);


--
-- Name: clubs clubs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clubs
    ADD CONSTRAINT clubs_pkey PRIMARY KEY (id);


--
-- Name: leagues leagues_league_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leagues
    ADD CONSTRAINT leagues_league_id_key UNIQUE (league_id);


--
-- Name: leagues leagues_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leagues
    ADD CONSTRAINT leagues_pkey PRIMARY KEY (id);


--
-- Name: player_availability player_availability_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_availability
    ADD CONSTRAINT player_availability_pkey PRIMARY KEY (id);


--
-- Name: player_availability player_availability_player_name_match_date_series_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_availability
    ADD CONSTRAINT player_availability_player_name_match_date_series_id_key UNIQUE (player_name, match_date, series_id);


--
-- Name: series_leagues series_leagues_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_leagues
    ADD CONSTRAINT series_leagues_pkey PRIMARY KEY (id);


--
-- Name: series_leagues series_leagues_series_id_league_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_leagues
    ADD CONSTRAINT series_leagues_series_id_league_id_key UNIQUE (series_id, league_id);


--
-- Name: series series_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series
    ADD CONSTRAINT series_name_key UNIQUE (name);


--
-- Name: series series_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series
    ADD CONSTRAINT series_pkey PRIMARY KEY (id);


--
-- Name: user_activity_logs user_activity_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_activity_logs
    ADD CONSTRAINT user_activity_logs_pkey PRIMARY KEY (id);


--
-- Name: user_instructions user_instructions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_instructions
    ADD CONSTRAINT user_instructions_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_club_leagues_club_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_club_leagues_club_id ON public.club_leagues USING btree (club_id);


--
-- Name: idx_club_leagues_league_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_club_leagues_league_id ON public.club_leagues USING btree (league_id);


--
-- Name: idx_leagues_league_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_leagues_league_id ON public.leagues USING btree (league_id);


--
-- Name: idx_player_availability; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_player_availability ON public.player_availability USING btree (player_name, match_date, series_id);


--
-- Name: idx_player_availability_date_series; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_player_availability_date_series ON public.player_availability USING btree (match_date, series_id);


--
-- Name: idx_player_availability_tenniscores_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_player_availability_tenniscores_id ON public.player_availability USING btree (tenniscores_player_id);


--
-- Name: idx_player_availability_unique_player_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_player_availability_unique_player_id ON public.player_availability USING btree (tenniscores_player_id, match_date, series_id) WHERE (tenniscores_player_id IS NOT NULL);


--
-- Name: idx_series_leagues_league_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_series_leagues_league_id ON public.series_leagues USING btree (league_id);


--
-- Name: idx_series_leagues_series_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_series_leagues_series_id ON public.series_leagues USING btree (series_id);


--
-- Name: idx_user_activity_logs_user_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_activity_logs_user_email ON public.user_activity_logs USING btree (user_email, "timestamp");


--
-- Name: idx_user_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_email ON public.users USING btree (email);


--
-- Name: idx_user_instructions_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_instructions_email ON public.user_instructions USING btree (user_email);


--
-- Name: idx_users_league_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_league_id ON public.users USING btree (league_id);


--
-- Name: idx_users_tenniscores_player_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_tenniscores_player_id ON public.users USING btree (tenniscores_player_id);


--
-- Name: club_leagues club_leagues_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_leagues
    ADD CONSTRAINT club_leagues_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id) ON DELETE CASCADE;


--
-- Name: club_leagues club_leagues_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_leagues
    ADD CONSTRAINT club_leagues_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(id) ON DELETE CASCADE;


--
-- Name: player_availability player_availability_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_availability
    ADD CONSTRAINT player_availability_series_id_fkey FOREIGN KEY (series_id) REFERENCES public.series(id);


--
-- Name: series_leagues series_leagues_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_leagues
    ADD CONSTRAINT series_leagues_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(id) ON DELETE CASCADE;


--
-- Name: series_leagues series_leagues_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.series_leagues
    ADD CONSTRAINT series_leagues_series_id_fkey FOREIGN KEY (series_id) REFERENCES public.series(id) ON DELETE CASCADE;


--
-- Name: users users_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id);


--
-- Name: users users_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- Name: users users_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_series_id_fkey FOREIGN KEY (series_id) REFERENCES public.series(id);


--
-- PostgreSQL database dump complete
--

