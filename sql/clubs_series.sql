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

--
-- Data for Name: clubs; Type: TABLE DATA; Schema: public; Owner: rossfreedman
--

INSERT INTO public.clubs (id, name) VALUES (1, 'Tennaqua');
INSERT INTO public.clubs (id, name) VALUES (2, 'Wilmette PD');
INSERT INTO public.clubs (id, name) VALUES (3, 'Sunset Ridge');
INSERT INTO public.clubs (id, name) VALUES (4, 'Winnetka');
INSERT INTO public.clubs (id, name) VALUES (5, 'Exmoor');
INSERT INTO public.clubs (id, name) VALUES (6, 'Hinsdale PC');
INSERT INTO public.clubs (id, name) VALUES (7, 'Onwentsia');
INSERT INTO public.clubs (id, name) VALUES (8, 'Salt Creek');
INSERT INTO public.clubs (id, name) VALUES (9, 'Lakeshore S&F');
INSERT INTO public.clubs (id, name) VALUES (10, 'Glen View');
INSERT INTO public.clubs (id, name) VALUES (11, 'Prairie Club');
INSERT INTO public.clubs (id, name) VALUES (12, 'Lake Forest');
INSERT INTO public.clubs (id, name) VALUES (13, 'Evanston');
INSERT INTO public.clubs (id, name) VALUES (14, 'Midt-Bannockburn');
INSERT INTO public.clubs (id, name) VALUES (15, 'Briarwood');
INSERT INTO public.clubs (id, name) VALUES (16, 'Birchwood');
INSERT INTO public.clubs (id, name) VALUES (17, 'Hinsdale GC');
INSERT INTO public.clubs (id, name) VALUES (18, 'Butterfield');
INSERT INTO public.clubs (id, name) VALUES (19, 'Chicago Highlands');
INSERT INTO public.clubs (id, name) VALUES (20, 'Glen Ellyn');
INSERT INTO public.clubs (id, name) VALUES (21, 'Skokie');
INSERT INTO public.clubs (id, name) VALUES (22, 'Winter Club');
INSERT INTO public.clubs (id, name) VALUES (23, 'Westmoreland');
INSERT INTO public.clubs (id, name) VALUES (24, 'Valley Lo');
INSERT INTO public.clubs (id, name) VALUES (25, 'South Barrington');
INSERT INTO public.clubs (id, name) VALUES (26, 'Saddle & Cycle');
INSERT INTO public.clubs (id, name) VALUES (27, 'Ruth Lake');
INSERT INTO public.clubs (id, name) VALUES (28, 'Northmoor');
INSERT INTO public.clubs (id, name) VALUES (29, 'North Shore');
INSERT INTO public.clubs (id, name) VALUES (30, 'Midtown - Chicago');
INSERT INTO public.clubs (id, name) VALUES (31, 'Michigan Shores');
INSERT INTO public.clubs (id, name) VALUES (32, 'Lake Shore CC');
INSERT INTO public.clubs (id, name) VALUES (33, 'Knollwood');
INSERT INTO public.clubs (id, name) VALUES (34, 'Indian Hill');
INSERT INTO public.clubs (id, name) VALUES (35, 'Glenbrook RC');
INSERT INTO public.clubs (id, name) VALUES (36, 'Hawthorn Woods');
INSERT INTO public.clubs (id, name) VALUES (37, 'Lake Bluff');
INSERT INTO public.clubs (id, name) VALUES (38, 'Barrington Hills CC');
INSERT INTO public.clubs (id, name) VALUES (39, 'River Forest PD');
INSERT INTO public.clubs (id, name) VALUES (40, 'Edgewood Valley');
INSERT INTO public.clubs (id, name) VALUES (41, 'Park Ridge CC');
INSERT INTO public.clubs (id, name) VALUES (42, 'Medinah');
INSERT INTO public.clubs (id, name) VALUES (43, 'LaGrange CC');
INSERT INTO public.clubs (id, name) VALUES (44, 'Dunham Woods');
INSERT INTO public.clubs (id, name) VALUES (45, 'Bryn Mawr');
INSERT INTO public.clubs (id, name) VALUES (46, 'Glen Oak');
INSERT INTO public.clubs (id, name) VALUES (47, 'Inverness');
INSERT INTO public.clubs (id, name) VALUES (48, 'White Eagle');
INSERT INTO public.clubs (id, name) VALUES (49, 'Legends');
INSERT INTO public.clubs (id, name) VALUES (50, 'River Forest CC');
INSERT INTO public.clubs (id, name) VALUES (51, 'Oak Park CC');
INSERT INTO public.clubs (id, name) VALUES (52, 'Royal Melbourne');
INSERT INTO public.clubs (id, name) VALUES (105, 'Germantown Cricket Club');
INSERT INTO public.clubs (id, name) VALUES (106, 'Philadelphia Cricket Club');
INSERT INTO public.clubs (id, name) VALUES (107, 'Merion Cricket Club');
INSERT INTO public.clubs (id, name) VALUES (108, 'Waynesborough Country Club');
INSERT INTO public.clubs (id, name) VALUES (109, 'Aronimink Golf Club');
INSERT INTO public.clubs (id, name) VALUES (110, 'Overbrook Golf Club');
INSERT INTO public.clubs (id, name) VALUES (111, 'Radnor Valley Country Club');
INSERT INTO public.clubs (id, name) VALUES (112, 'White Manor Country Club');


--
-- Data for Name: series; Type: TABLE DATA; Schema: public; Owner: rossfreedman
--

INSERT INTO public.series (id, name) VALUES (1, 'Chicago 1');
INSERT INTO public.series (id, name) VALUES (2, 'Chicago 2');
INSERT INTO public.series (id, name) VALUES (3, 'Chicago 3');
INSERT INTO public.series (id, name) VALUES (4, 'Chicago 4');
INSERT INTO public.series (id, name) VALUES (5, 'Chicago 5');
INSERT INTO public.series (id, name) VALUES (6, 'Chicago 6');
INSERT INTO public.series (id, name) VALUES (7, 'Chicago 7');
INSERT INTO public.series (id, name) VALUES (8, 'Chicago 8');
INSERT INTO public.series (id, name) VALUES (9, 'Chicago 9');
INSERT INTO public.series (id, name) VALUES (10, 'Chicago 10');
INSERT INTO public.series (id, name) VALUES (11, 'Chicago 11');
INSERT INTO public.series (id, name) VALUES (12, 'Chicago 12');
INSERT INTO public.series (id, name) VALUES (13, 'Chicago 13');
INSERT INTO public.series (id, name) VALUES (14, 'Chicago 14');
INSERT INTO public.series (id, name) VALUES (15, 'Chicago 15');
INSERT INTO public.series (id, name) VALUES (16, 'Chicago 16');
INSERT INTO public.series (id, name) VALUES (17, 'Chicago 17');
INSERT INTO public.series (id, name) VALUES (18, 'Chicago 18');
INSERT INTO public.series (id, name) VALUES (19, 'Chicago 19');
INSERT INTO public.series (id, name) VALUES (20, 'Chicago 20');
INSERT INTO public.series (id, name) VALUES (21, 'Chicago 21');
INSERT INTO public.series (id, name) VALUES (22, 'Chicago 22');
INSERT INTO public.series (id, name) VALUES (23, 'Chicago 23');
INSERT INTO public.series (id, name) VALUES (24, 'Chicago 24');
INSERT INTO public.series (id, name) VALUES (25, 'Chicago 25');
INSERT INTO public.series (id, name) VALUES (26, 'Chicago 26');
INSERT INTO public.series (id, name) VALUES (27, 'Chicago 27');
INSERT INTO public.series (id, name) VALUES (28, 'Chicago 28');
INSERT INTO public.series (id, name) VALUES (29, 'Chicago 29');
INSERT INTO public.series (id, name) VALUES (30, 'Chicago 30');
INSERT INTO public.series (id, name) VALUES (31, 'Chicago 31');
INSERT INTO public.series (id, name) VALUES (32, 'Chicago 32');
INSERT INTO public.series (id, name) VALUES (33, 'Chicago 33');
INSERT INTO public.series (id, name) VALUES (34, 'Chicago 34');
INSERT INTO public.series (id, name) VALUES (35, 'Chicago 35');
INSERT INTO public.series (id, name) VALUES (36, 'Chicago 36');
INSERT INTO public.series (id, name) VALUES (37, 'Chicago 37');
INSERT INTO public.series (id, name) VALUES (38, 'Chicago 38');
INSERT INTO public.series (id, name) VALUES (39, 'Chicago 39');
INSERT INTO public.series (id, name) VALUES (40, 'Chicago Legends');
INSERT INTO public.series (id, name) VALUES (41, 'Chicago 7 SW');
INSERT INTO public.series (id, name) VALUES (42, 'Chicago 9 SW');
INSERT INTO public.series (id, name) VALUES (43, 'Chicago 11 SW');
INSERT INTO public.series (id, name) VALUES (44, 'Chicago 13 SW');
INSERT INTO public.series (id, name) VALUES (45, 'Chicago 15 SW');
INSERT INTO public.series (id, name) VALUES (46, 'Chicago 17 SW');
INSERT INTO public.series (id, name) VALUES (47, 'Chicago 19 SW');
INSERT INTO public.series (id, name) VALUES (48, 'Chicago 21 SW');
INSERT INTO public.series (id, name) VALUES (49, 'Chicago 23 SW');
INSERT INTO public.series (id, name) VALUES (50, 'Chicago 25 SW');
INSERT INTO public.series (id, name) VALUES (51, 'Chicago 27 SW');
INSERT INTO public.series (id, name) VALUES (52, 'Chicago 29 SW');
INSERT INTO public.series (id, name) VALUES (105, 'Series 1');
INSERT INTO public.series (id, name) VALUES (106, 'Series 2');
INSERT INTO public.series (id, name) VALUES (107, 'Series 3');
INSERT INTO public.series (id, name) VALUES (108, 'Series 4');
INSERT INTO public.series (id, name) VALUES (109, 'Series 5');
INSERT INTO public.series (id, name) VALUES (110, 'Series 6');
INSERT INTO public.series (id, name) VALUES (111, 'Series 7');
INSERT INTO public.series (id, name) VALUES (112, 'Series 8');


--
-- Name: clubs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rossfreedman
--

SELECT pg_catalog.setval('public.clubs_id_seq', 180, true);


--
-- Name: series_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rossfreedman
--

SELECT pg_catalog.setval('public.series_id_seq', 180, true);


--
-- PostgreSQL database dump complete
--

