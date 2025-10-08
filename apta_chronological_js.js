
  $(document).on('ready', function(){
  $('#playercard_value_losses').html('0');
  $('#playercard_value_wins').html('0');
    $('#match_types').on('change', function(){
  $('.match_type_All').hide();
  $('.match_type_'+$(this).val()).show();
  });

  $('#chron').on('change', function(){
  {
	if($('#chron').is(':checked'))
	window.location.href='/?print&mod=nndz-Sm5yb2lPdTcxdFJibXc9PQ%3D%3D&all&p=nndz-WkNBPQ%3D%3D';
	else
		window.location.href='/?print&mod=nndz-Sm5yb2lPdTcxdFJibXc9PQ%3D%3D&p=nndz-WkNBPQ%3D%3D';
  }});



  });
  var matchcardt = 0;
  function matchCardToggle()
  {
  if(matchcardt==0)
  {
	$('.match_card').show();
	matchcardt = 1;
  }
  else
  {
	$('.match_card').hide();
	matchcardt = 0;
  }
  }

  
