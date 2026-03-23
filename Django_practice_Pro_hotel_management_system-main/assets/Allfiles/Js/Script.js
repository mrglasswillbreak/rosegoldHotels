$(function () {
    //slide part js
    $('.late').textillate({
        loop: true,
        minDisplayTime: 3000,
        initialDelay: 1000,
        in: {
            effect: 'bounceInDown',
            delayScale: 2,
        },
        out: {
            effect: 'bounce',
            delayScale: 1,
            shuffle: true,
        },
    });
    
    //slide part js
    $('#slider').slick({
        dots: false,
        autoplay: true,
        autoplaySpeed: 5000,
        prevArrow: '.pre_btn',
        nextArrow: '.next_btn',
    });

    //Book A Table Area js
    $('.Check_in ').datetimepicker({
        formatTime: 'H:i:i',
        formatDate: 'd.m.Y',
        theme: 'dark',
        step: 30,
        hours12: false,
    });
    $('.open').click(function () {
        $('.Check_in').datetimepicker('show');
    });
 
    $('.Check_out ').datetimepicker({
        formatTime: 'H:i:i',
        formatDate: 'd.m.Y',
        theme: 'dark',
        step: 30,
        hours12: false,
        
    });
    $('.open1').click(function () {
        $('.Check_out').datetimepicker('show');
    });
    // about part js
  $(".video_btn").modalVideo({
    theme: 'dark',
    });
  // EXPLOR OUR ROOMS js
    $('.room_slide').slick({
        autoplay: true,
        autoplaySpeed:2000,
        slidesToShow:3,
        slidesToScroll:2,
        dots: true,
        arrows:false,
        responsive: [
            {
                breakpoint: 992,
                settings: {
                    slidesToShow: 2,
                    slidesToScroll: 1
                }
            },
            {
                breakpoint: 576,
                settings: {
                    slidesToShow: 1,
                    slidesToScroll: 1
                }
            }
        ]
    });
  //OUR AWESOME SERVICES js
    
    $('#example').tabs({
        delay: 500,
    });

   //OUR GALLERY js
    $('.gallary_overly').magnificPopup({
    type: 'image',
    gallery: {
      enabled: true,
      tPrev: 'Gallery_pre', 
      tNext: 'Gallery_next', 
    },
    });

    $('.GALLERY_slider').slick({
        autoplay: true,
        autoplaySpeed:2000,
        slidesToShow:4,
        slidesToScroll:2,
        dots: true,
        arrows:false,
        responsive: [
            {
                breakpoint: 992,
                settings: {
                    slidesToShow: 2,
                    slidesToScroll: 1
                }
            },
            {
                breakpoint: 576,
                settings: {
                    slidesToShow: 1,
                    slidesToScroll: 1
                }
            }
        ]
    });

      //Our Special Staff Part start
     $('.Staff_slider').slick({
        autoplay: true,
        autoplaySpeed:2000,
        slidesToShow:4,
        slidesToScroll:2,
        dots: true,
        arrows:false,
        responsive: [
            {
                breakpoint: 992,
                settings: {
                    slidesToShow: 2,
                    slidesToScroll: 1
                }
            },
            {
                breakpoint: 576,
                settings: {
                    slidesToShow: 1,
                    slidesToScroll: 1
                }
            }
        ]
    });

    // Initialize accessibility attributes for Staff cards
    $('#Staff .Staff_info').each(function () {
        var $card = $(this);
        var isActive = $card.hasClass('active');
        $card.attr({
            tabindex: '0',
            role: 'button',
            'aria-expanded': isActive ? 'true' : 'false'
        });
        var $links = $card.find('.Staff_part2');
        if ($links.length) {
            $links.attr('aria-hidden', isActive ? 'false' : 'true');
        }
    });

    // Helper to toggle Staff card social links and keep ARIA in sync
    function toggleStaffCard($card) {
        if (!$card || !$card.length) return;

        var wasActive = $card.hasClass('active');

        // Deactivate all cards and hide their social links
        $('#Staff .Staff_info').each(function () {
            var $c = $(this);
            $c.removeClass('active').attr('aria-expanded', 'false');
            var $links = $c.find('.Staff_part2');
            if ($links.length) {
                $links.attr('aria-hidden', 'true');
            }
        });

        // If the card was not active, activate it and show its social links
        if (!wasActive) {
            $card.addClass('active').attr('aria-expanded', 'true');
            var $cardLinks = $card.find('.Staff_part2');
            if ($cardLinks.length) {
                $cardLinks.attr('aria-hidden', 'false');
            }
        }
    }

    // Staff card social links: toggle on click/tap for touch devices
    $(document).on('click', '#Staff .Staff_info', function(e) {
        // Allow clicks on the social links themselves to pass through
        if ($(e.target).closest('.Staff_part2').length) return;
        toggleStaffCard($(this));
    });

    // Keyboard support for Staff cards (Enter/Space)
    $(document).on('keydown', '#Staff .Staff_info', function (e) {
        var key = e.key || e.keyCode;
        if (key === 'Enter' || key === 13 || key === ' ' || key === 32) {
            e.preventDefault();
            toggleStaffCard($(this));
        }
    });
   
   //counter part js
    $('.counter').counterUp({
      delay:5,
      time: 1000,
      });  
 
 
});