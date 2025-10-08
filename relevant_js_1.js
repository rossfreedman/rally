
function inIframe () {
    try {
        return window.self !== window.top;
    } catch (e) {
        return true;
    }
}
//if(inIframe())
{
  //window.location.href = 'http://google.com';
}
psearchclicker = 0;
$(document).ready(function(){


$('.form-tooltip-img').on('mouseenter', function(){
                $('.form-tooltip-info').hide();
                $('#form-'+$(this).attr('id')).show();
        });
$('.form-tooltip-img').on('mouseleave', function(){
                $('.form-tooltip-info').hide();
        });

$('#FLASHBADCLICK').trigger('click');
/*  $('#psearchclicker').on('click', function(){
    $('#psearchdiv').show();
    psearchclicker++;
    if(psearchclicker>1)
      $('#psearchform').submit();
    return false;
  });*/

  $('#site_linker_drop_link').on('mouseenter', function(){
    $('#site_linker_drop_div').show();
  });
  $('#site_linker_drop_link').on('mouseleave', function(){
$('#site_linker_drop_div').hide();
});
  $('#site_linker_drop_link2').on('mouseenter', function(){
    $('#site_linker_drop_div2').show();
  });
  $('#site_linker_drop_link2').on('mouseleave', function(){
$('#site_linker_drop_div2').hide();
  });

  $('#rulesdroplink').on('mouseenter', function(){
    $('#rulesdropdiv').show();
});
  $('#rulesdroplink').on('mouseleave', function(){
    $('#rulesdropdiv').hide();
});
  $('#formsdroplink').on('mouseenter', function(){
    $('#formsdropdiv').show();
});
  $('#formsdroplink').on('mouseleave', function(){
    $('#formsdropdiv').hide();
});
  $('#aboutusdroplink').on('mouseenter', function(){
    $('#aboutusdropdiv').show();
});
  $('#aboutusdroplink').on('mouseleave', function(){
    $('#aboutusdropdiv').hide();
  });

  $('#apta_topblack .apta_topwhite_itemer').on('mouseleave', function(){
    $('#apta_topblack .apta_topwhite_itemer').removeClass('apta_topwhite_itemer_selected');
    $('#apta_topblack .apta_topwhite_itemer'+which).addClass('apta_topwhite_itemer_selected');
  });
  $('#apta_topblack .apta_topwhite_itemer').on('mouseenter', function(){
    $('#apta_topblack .apta_topwhite_itemer').removeClass('apta_topwhite_itemer_selected');
    $(this).addClass('apta_topwhite_itemer_selected');
  });
  });

jQuery.fn.extend({
    label: function() {
        return $(this.map(function() {
            var field = $(this); var label;
            var id = field.attr("id");
            label = $("label[for="+id+"]")[0];
            return label;
        }));},
    default_value: function(value) {
    var $this = $(this);
        if($this.val()==""){
            this.closest("form").bind("submit pre-ajax-submit", remove_default_values_callback);
            this.bind('change', function(){
            $this.removeClass('default-value');
            });
            return this.addClass("default-value").bind('focus', default_value_callback)
                .bind("blur", function(){$this.default_value(value)})
                .val(value);

        }else{
            return this;
        }
        },
        _cs_datepicker: function() {
          try{
        return this.datepicker({
            buttonImage: "/calendar.png",
            showOn: "both", yearRange: "-100:+2",  dateFormat: "yy-mm-dd", buttonImageOnly: true, changeYear: true});
            }
          catch(err){}
        },
        _cs_datepickernoyear: function() {
          try{
        return this.datepicker({
            buttonImage: "/calendar.png",
            showOn: "both", dateFormat: "mm/dd", buttonImageOnly: true, changeYear: false});
            }
          catch(err){}
        },

        });
function default_value_callback(){
    $(this).removeClass("default-value").val("").unbind("focus", default_value_callback);
}
function remove_default_values_callback(){
    $(this).find(".default-value").each(function(){$(this).val("")});
    return true;
}
$(document).ready(function(){
    $("[data-default-value]", $(document)).each(function(){
        $(this).default_value($(this).attr("data-default-value"));
    });
    $("input,select,textarea", document).focus(function(){
        $(this).addClass("has-been-focused");});
});

$(document).ready(function(){
  $(".datepicker", $(document))._cs_datepicker();
  $(".datepickernoyear", $(document))._cs_datepickernoyear();
});
