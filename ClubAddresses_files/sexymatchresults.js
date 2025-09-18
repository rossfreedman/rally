var offset = 0;

function highlight_game(schedule, playoff)
{
	s = document.getElementById(schedule);
	if (s != null)
	{
		if (myopen == schedule) s.className = "active std fancy";
		else s.className = "active std fancy";
		if(playoff=='1')s.className = "playoff playoffon";
		return;
	}
	h = document.getElementById("h" + schedule);
	a = document.getElementById("a" + schedule);
	if (h == null || a == null) return;
	if (myopen != schedule)
	{
		h.className = "active std fancy";
		a.className = "active std fancy";
		if(playoff=='1'){h.className = "playoff playoffon";a.className = "playoff playoffon";}
	}
	else
	{
		h.className = "active std fancy";
		a.className = "active std fancy";
		if(playoff=='1'){h.className = "playoff playoffon";a.className = "playoff playoffon";}
	}
}

function unhighlight_game(schedule, playoff)
{
	s = document.getElementById(schedule);
	if (s != null && myopen != schedule)
	{
		s.className = "std fancy";
		if(playoff=='1')s.className = "playoff playoffoff";
		return;
	}
	h = document.getElementById("h" + schedule);
	a = document.getElementById("a" + schedule);
	if (h == null || a == null) return;
	if (myopen != schedule)
	{
		h.className = "std fancy";
		a.className = "std fancy";
		if(playoff=='1'){h.className = "playoff playoffoff";a.className = "playoff playoffoff";}
	}
}

//var effect = null;
//var fading = null;
var myopen = null;

function player_showscorecard(user, schedule)
{
	showscorecard(schedule);
	myopen = user + "" + schedule;
	highlight_game(myopen);
}

function showscorecard(schedule)
{
	/*
	if (effect != null)
	{
		fading = schedule;
	}
	else
	{
	*/
		var scorecard = document.getElementById("scorecard");
		scorecard.style.visibility = "hidden";
		var oldopen = myopen;
		myopen = schedule;
		if (oldopen != null) unhighlight_game(oldopen);
		highlight_game(schedule);
		makeRequest(schedule);
	/*
	}
	*/
}

function makeRequest(schedule)
{
	var e = document.getElementById("instructions");
	e.className = "hidden";
	showSpinner();
	var xmlhttp = getXmlHttpRequestObject();
	var url = "/ajax/scorecard.php?s=" + schedule;
	url += "&random=" + Math.floor(Math.random()*32768);
	xmlhttp.open("GET", url, true);
	xmlhttp.onreadystatechange = 
	function ()
	{
		if (xmlhttp.readyState == 4)
		{
			hideSpinner();
			var scorecard = document.getElementById("scorecard");
			//scorecard.innerHTML = "<div>" + xmlhttp.responseText + "</div>";
			scorecard.innerHTML = xmlhttp.responseText + "</div>";
			scorecard.style.visibility = "";

			/*
			effect = new Spry.Effect.Fade(
				"scorecard",
				{
					duration: 500, from:"0%", to:"100%", 
					finish: function()
					{
						effect = null;
						if (fading != null)
						{
							var s = fading;
							fading = null;
							showscorecard(s);
						}
					}
				}
			);
			effect.start();
			*/

		}
		return true;
	}
	xmlhttp.send(null);
	return true;
}

function shift_right()
{
    goRight();
    return;
	if (offset < weeks.length - max)
	{
		col = weeks[offset];
		for(var i=0; i<col.length; i++)
		{
		    try{
			e = document.getElementById(col[i]);
			e.className = "hidden";
		    }catch(err){}
		}
		col = weeks[offset+max];
		for(var i=0; i<col.length; i++)
		{
		    try{
			e = document.getElementById(col[i]);
			s = col[i].substring(1);
			d = e.id.substr(0,1);
			if(d=='x')
			    e.className = "";
			else if (myopen == s)
			    e.className = "std fancy active"
		        else
			    e.className = "std fancy";
		    }catch(err){}//dunno what to do, just being honest
		}
		offset++;
	}
}

function shift_left()
{
    goLeft();
    return;
	if (offset > 0)
	{
		offset--;
		col = weeks[offset];
		for(var i=0; i<col.length; i++)
		{
		    try{
			e = document.getElementById(col[i]);
			s = col[i].substring(1);
			d = e.id.substr(0,1);
			if(d=='x')
			    e.className = "";
			else if (jQuery.inArray(s, playoffs)!=-1)
				e.className = "playoff";
			else if (myopen == s)
				e.className = "std fancy active"
			else
				e.className = "std fancy";
		    }
		    catch(e){}
		}
		col = weeks[offset+max];
		for(var i=0; i<col.length; i++)
		{
		    try{
			e = document.getElementById(col[i]);
			e.className = "hidden";
		    }
		    catch(e){}
		}
	}
}
