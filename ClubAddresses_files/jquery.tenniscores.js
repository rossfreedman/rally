/// <reference path="jquery-vsdoc.js" />
$(document).ready(function() {
    //png fix
    $(document).pngFix(); 
    //league search
    $('input[name="league-search"]').focus(function() {
	    if ($(this).attr('value') == 'Find a League' || $(this).attr('value')== 'Type in league name or city')
            $(this).attr('value', '');
    });
    $('input[name="league-search"]').blur(function() {
        var text = $(this).val();
        if (text == '')
            $(this).attr('value', 'Find a League');
    });


    //intialize default lightbox links
    $('a.lightbox').fancybox({
        'overlayColor': '#000',
	    'overlayOpacity': 0.6,
    });
    //intialize small lightbox links
    $('a.lightbox-320').fancybox({
        'overlayColor': '#000',
        'overlayOpacity': 0.6,
        'overlayShow': true,
        'width': 320,
        'height': 500,

    });
    //intialize medium lightbox links
    $('a.lightbox-800-wide').fancybox({
        'overlayColor': '#000',
        'overlayOpacity': 0.6,
        'overlayShow': true,
        'width': 800,
	'height': 450, 
	'hideOnContentClick': false,

    });

    $('a.lightbox-540').fancybox({
        'overlayColor': '#000',
        'overlayOpacity': 0.6,
        'overlayShow': true,
        'width': 540,
	'height': 500, 
	'hideOnContentClick': false,

    });
    $('a.lightbox-auto').fancybox({
        'overlayColor': '#000',
        'overlayOpacity': 0.6,
        'overlayShow': true,
        'width': 800,
	'height': 760,
	'autoScale': true,
	'hideOnContentClick': false,

    });
    //intialize medium-tall lightbox links
    $('a.lightbox-540-tall').fancybox({
        'overlayColor': '#000',
        'overlayOpacity': 0.6,
        'overlayShow': true,
	    'padding': 0,
	    'autoScale': false,
        'width': 540,
        'height': 975,
	'centerOnScroll': false,
	'hideOnContentClick': false,
    });
    //intialize large lightbox links
    $('a.lightbox-760').fancybox({
        'overlayColor': '#000',
        'overlayOpacity': 0.6,
        'overlayShow': true,
        'width': 760,
        'height': 540,

    });

    //intialize large lightbox links
    $('a.lightbox-760-tall').fancybox({
        'overlayColor': '#000',
        'overlayOpacity': 0.6,
        'overlayShow': true,
        'width': 760,
	    'height': 740,
	'centerOnScroll': false,
    });


    $('a.lightbox-600').fancybox({
        'overlayColor': '#000',
        'overlayOpacity': 0.6,
        'overlayShow': true,
        'width': 600,
	    'height': 540,
	    'padding': 0,
    });




    //function for each tab containers
    $('#internal-body-left .tabbed-cont').each(function() {
        //determine width of container
        var width = 610;

        //count number of tabs
        var tabs = $(this).children('ul').children('li').size();

        //set width of each tab
        $(this).children('ul').children('li').width(width / tabs);



    });
    $('#internal-body-right .tabbed-cont').each(function() {
        //determine width of container
        var width = 305;

        //count number of tabs
        var tabs = $(this).children('ul').children('li').size();

        //set width of each tab
        $(this).children('ul').children('li').width(width / tabs);



    });
    $('.main-width .tabbed-cont').each(function() {
        //determine width of container
        var width = 610;

        //count number of tabs
        var tabs = $(this).children('ul').children('li').size();

        //set width of each tab
        $(this).children('ul').children('li').width(width / tabs);



    });
    $('.side-width .tabbed-cont').each(function() {
        //determine width of container
        var width = 305;

        //count number of tabs
        var tabs = $(this).children('ul').children('li').size();

        //set width of each tab
        $(this).children('ul').children('li').width(width / tabs);



    });
    $('.lg-main-width .tabbed-cont').each(function() {
	    if($(this).hasClass('ignore')){return false;}

        //determine width of container
        var width = 695;

        //count number of tabs
        var tabs = $(this).children('ul').children('li').size();

        //set width of each tab
	//        $(this).children('ul').children('li').width(width / tabs);



    });
    $('.sm-side-width .tabbed-cont').each(function() {
        //determine width of container
        var width = 220;

        //count number of tabs
        var tabs = $(this).children('ul').children('li').size();

        //set width of each tab
        $(this).children('ul').children('li').width(width / tabs);



    });

    //attach click function to tabs
    $('ul.tabs li, ul.tabbers li').each(function() {
	    if($(this).hasClass('ignoreli'))return false;
    //hide all tab content
    $(this).parent('ul').parent('.tabbed-cont').find('.content').hide();
    //Add class active to first tab
    $(this).parent('ul').parent('.tabbed-cont').find('ul.tabs li:first a, ul.tabbers li:first a').addClass('active');
    //Show first tab content
    $(this).parent('ul').parent('.tabbed-cont').find('.tab-body .content:first').show();
    $(this).click(function() {
        $(this).parent('ul').find('a').removeClass('active');
        var activeTab = $(this).find('a').attr('class');
	var arr = activeTab.split(' ');
	for(asdf=0; asdf<arr.length; asdf++)
	    {
		if(arr[asdf].substr(0, 4)=='#tab')
		    {
			activeTab = arr[asdf];
			break;
		    }
	    }
        $(this).children('a').addClass('active');
        $(this).parent('ul').parent('.tabbed-cont').find('.content').hide();
        $(activeTab).fadeIn();
        });
        

    });


})

   
