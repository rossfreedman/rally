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
-- Name: series id; Type: DEFAULT; Schema: public; Owner: rossfreedman
--

ALTER TABLE ONLY public.series ALTER COLUMN id SET DEFAULT nextval('public.series_id_seq'::regclass);


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
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: rossfreedman
--

COPY public.users (id, email, password_hash, first_name, last_name, club_id, series_id, club_automation_password, created_at, last_login) FROM stdin;
8	jessfreedman@gmail.com	pbkdf2:sha256:1000000$30H2lfQJefbpXSQ9$bc29fb0d6b2605362513fd9aefedfe4dc77a591de9d478a8d5f8794c20912d27	Jess	Freedman	1	19	\N	2025-05-18 19:42:01.24637	\N
9	aseyb@aol.com	pbkdf2:sha256:1000000$bveYOeds3wJgJq9G$6bdd560cca5c75857bd6fc7c53e9692c6bede9c150d21109423e7ccfe3ac93c2	Adam	Seyb	1	22	\N	2025-05-18 20:29:50.860784	\N
7	rossfreedman@gmail.com	pbkdf2:sha256:1000000$fsxkBUxUvatei6gz$322d074c5e8035fb7688a0a53cbc0a6aeba587a3ad9eb066b70372d29554166c	Ross	Freedman	1	22	\N	2025-05-18 11:31:24.509828	2025-05-18 21:50:12.860884
\.


--
-- Name: clubs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rossfreedman
--

SELECT pg_catalog.setval('public.clubs_id_seq', 180, true);


--
-- Name: series_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rossfreedman
--

SELECT pg_catalog.setval('public.series_id_seq', 180, true);


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
-- Name: idx_user_email; Type: INDEX; Schema: public; Owner: rossfreedman
--

CREATE INDEX idx_user_email ON public.users USING btree (email);


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

