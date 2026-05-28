$(function () {
    var swiperPartner = new Swiper('.swiper.swiperPartner', {
        autoplay: {
            delay: 3000
        },
        speed: 2000,
        slidesPerView: 3,
        slidesPerGroup: 1,
        spaceBetween: 10,
        loop: false,
        grabCursor: true,
        breakpoints: {
            // when window width is >= 360px
            360: {
                slidesPerView: 2,
                slidesPerGroup: 1,
            },
            // when window width is >= 768px
            768: {
                slidesPerView: 2,
                slidesPerGroup: 1,
            },
            // when window width is >= 1024px
            1024: {
                slidesPerView: 3,
                slidesPerGroup: 1,
            }
        },
        // If we need pagination
        pagination: {
            enabled: false,
            el: '.swiper-pagination',
            type: 'bullets',
            clickable: true,
        },
    });

});

$(function () {
    var swiperCard = new Swiper('.swiper.swiperCard', {
        autoplay: {
            delay: 6000
        },
        speed: 2000,
        slidesPerView: 3,
        slidesPerGroup: 2,
        spaceBetween: 10,
        loop: false,
        grabCursor: true,
        breakpoints: {
            // when window width is >= 360px
            360: {
                slidesPerView: 1,
            },
            // when window width is >= 768px
            768: {
                slidesPerView: 3,
            },
            // when window width is >= 1024px
            1024: {
                slidesPerView: 3,
            }
        },
        // If we need navigation
        navigation: {
            nextEl: ".swiper-button-next",
            prevEl: ".swiper-button-prev",
        },
    });

});

$(function () {
    var swiperTeam = new Swiper('.swiper.swiperTeam', {
        autoplay: {
            delay: 5000
        },
        speed: 2000,
        slidesPerView: 1.5,
        slidesPerGroup: 2,
        spaceBetween: 10,
        loop: false,
        grabCursor: true,
        breakpoints: {
            // when window width is >= 360px
            360: {
                slidesPerView: 1,
            },
            // when window width is >= 768px
            768: {
                slidesPerView: 1.5,
            },
            // when window width is >= 1024px
            1024: {
                slidesPerView: 1.5,
            }
        },
        // If we need pagination
        pagination: {
            enabled: true,
            el: '.swiper-pagination',
            type: 'bullets',
            clickable: true,
        },
    });

});

var swiperTestimonials = new Swiper(".swiperTestimonials", {
    autoplay: {
        delay: 4000
    },
    speed: 3000,
    effect: "coverflow",
    initialSlide: 1,
    loop: true,
    grabCursor: true,
    centeredSlides: true,
    slidesPerView: 2,
    coverflowEffect: {
        rotate: 0,
        stretch: 0,
        depth: 100,
        modifier: 0,
        slideShadows: false
    },
    breakpoints: {
        // when window width is >= 360px
        360: {
            slidesPerView: 1,
            effect: "coverflow",
            coverflowEffect: {
                scale: 1,
                modifier: 2,
                depth: 200,
            }
        },
        // when window width is >= 768px
        768: {
            slidesPerView: 1,
            effect: "coverflow",
            coverflowEffect: {
                scale: 1,
                modifier: 2,
                depth: 200,
            }
        },
        // when window width is >= 1024px
        1024: {
            slidesPerView: 2,
        }
    },
    pagination: {
        el: ".swiper-pagination"
    }
});

var swiperService = new Swiper(".swiperService", {
    autoplay: {
        delay: 5000
    },
    speed: 2000,
    effect: "coverflow",
    initialSlide: 1,
    loop: false,
    grabCursor: true,
    centeredSlides: true,
    slidesPerView: 3,
    coverflowEffect: {
        rotate: 0,
        stretch: 0,
        depth: 100,
        modifier: 0,
        scale: 1,
        slideShadows: true
    },
    breakpoints: {
        // when window width is >= 360px
        360: {
            slidesPerView: 1,
            effect: "coverflow",
            coverflowEffect: {
                scale: 1,
                modifier: 2,
                depth: 200,
            }
        },
        // when window width is >= 768px
        768: {
            slidesPerView: 1,
            effect: "coverflow",
            coverflowEffect: {
                scale: 1,
                modifier: 2,
                depth: 200,
            }
        },
        // when window width is >= 1024px
        1024: {
            slidesPerView: 3,
        }
    },
    // If we need pagination
    pagination: {
        enabled: true,
        el: '.swiper-pagination',
        type: 'bullets',
        clickable: true,
    }
});

$(function () {
    var swiperImage = new Swiper('.swiper.swiperImage', {
        speed: 2000,
        slidesPerView: 1,
        slidesPerGroup: 1,
        spaceBetween: 20,
        loop: false,
        grabCursor: true,
        breakpoints: {
            // when window width is >= 360px
            360: {
                slidesPerView: 1,
            },
            // when window width is >= 768px
            768: {
                slidesPerView: 1,
            },
            // when window width is >= 1024px
            1024: {
                slidesPerView: 1,
            }
        },
        // If we need pagination
        pagination: {
            enabled: true,
            el: '.swiper-pagination',
            type: 'bullets',
            clickable: true,
        },
    });

});

$(function () {
    var swiperImage2 = new Swiper('.swiper.swiperImage2', {
        autoplay: {
            delay: 6000
        },
        speed: 2000,
        slidesPerView: 4,
        slidesPerGroup: 2,
        spaceBetween: 10,
        loop: false,
        grabCursor: true,
        breakpoints: {
            // when window width is >= 360px
            360: {
                slidesPerView: 1,
            },
            // when window width is >= 768px
            768: {
                slidesPerView: 4,
            },
            // when window width is >= 1024px
            1024: {
                slidesPerView: 4,
            }
        },
        // If we need pagination
        pagination: {
            enabled: true,
            el: '.swiper-pagination',
            type: 'bullets',
            clickable: true,
        },
    });

});


