%define nginx_name      nginx
%define nginx_version   1.2.2
%define nginx_user      nginx
%define nginx_group     %{nginx_user}
%define nginx_home      %{_localstatedir}/lib/nginx
%define nginx_home_tmp  %{nginx_home}/tmp
%define nginx_logdir    %{_localstatedir}/log/nginx
%define nginx_confdir   %{_sysconfdir}/nginx
%define nginx_datadir   %{_datadir}/nginx
%define nginx_webroot   %{nginx_datadir}/html
%define passenger_version   3.0.13

Name:           nginx-passenger
Version:        %{nginx_version}+%{passenger_version}
Release:        2%{?dist}
Summary:        Robust, small and high performance http and reverse proxy server
Group:          System Environment/Daemons

# BSD License (two clause)
# http://www.freebsd.org/copyright/freebsd-license.html
License:        BSD
URL:            http://nginx.net/
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-%(%{__id_u} -n)

BuildRequires:      pcre-devel,zlib-devel,openssl-devel
Requires:           pcre,zlib,openssl
# for /usr/sbin/useradd
Requires(pre):      shadow-utils
Requires(post):     chkconfig
# for /sbin/service
Requires(preun):    chkconfig, initscripts
Requires(postun):   initscripts

Source0:    http://nginx.org/download/nginx-%{nginx_version}.tar.gz
Source1:    %{nginx_name}.init
Source2:    %{nginx_name}.conf

Patch0:     nginx-install-sbin.patch

%description
Nginx [engine x] is an HTTP(S) server, HTTP(S) reverse proxy and IMAP/POP3
proxy server written by Igor Sysoev.

%prep
%setup -q -n %{nginx_name}-%{nginx_version}

%patch0 -p1

%{__cat} <<EOF >%{nginx_name}.logrotate
%{nginx_logdir}/*log {
    daily
    rotate 10
    missingok
    notifempty
    compress
    sharedscripts
    postrotate
        [ ! -f /var/run/nginx.pid ] || kill -USR1 `cat %{_localstatedir}/run/%{nginx_name}.pid`
    endscript
}
EOF

%{__cat} <<EOF >%{nginx_name}.sysconfig
# Configuration file for the %{nginx_name} service

# set this to the location of the %{nginx_name} configuration file
NGINX_CONF_FILE=%{nginx_confdir}/%{nginx_name}.conf
EOF


%build
# compile support for nginx in passenger
MY_BUILD_DIR=`pwd`
cd `passenger-config --root`
rake nginx
cd $MY_BUILD_DIR

# nginx does not utilize a standard configure script.  It has its own
# and the standard configure options cause the nginx configure script
# to error out.  This is is also the reason for the DESTDIR environment
# variable.  The configure script(s) have been patched (Patch1 and
# Patch2) in order to support installing into a build environment.
export DESTDIR=%{buildroot}
./configure \
    --user=%{nginx_user} \
    --group=%{nginx_group} \
    --prefix=%{nginx_datadir} \
    --sbin-path=%{_sbindir}/%{nginx_name} \
    --conf-path=%{nginx_confdir}/%{nginx_name}.conf \
    --error-log-path=%{nginx_logdir}/error.log \
    --http-log-path=%{nginx_logdir}/access.log \
    --http-client-body-temp-path=%{nginx_home_tmp}/client_body \
    --http-proxy-temp-path=%{nginx_home_tmp}/proxy \
    --http-fastcgi-temp-path=%{nginx_home_tmp}/fastcgi \
    --pid-path=%{_localstatedir}/run/%{nginx_name}.pid \
    --lock-path=%{_localstatedir}/lock/subsys/%{nginx_name} \
    --with-http_ssl_module \
    --with-http_gzip_static_module \
    --with-http_realip_module \
    --with-http_addition_module \
    --with-http_sub_module \
    --with-http_stub_status_module \
    --with-ipv6 \
    --with-http_secure_link_module \
    --with-http_flv_module \
    --with-http_mp4_module \
    --add-module=`passenger-config --root`/ext/nginx
make %{?_smp_mflags}

%install
rm -rf %{buildroot}
make install DESTDIR=%{buildroot} INSTALLDIRS=vendor
find %{buildroot} -type f -name .packlist -exec rm -f {} \;
find %{buildroot} -type f -name perllocal.pod -exec rm -f {} \;
find %{buildroot} -type f -empty -exec rm -f {} \;
find %{buildroot} -type f -exec chmod 0644 {} \;
find %{buildroot} -type f -name '*.so' -exec chmod 0755 {} \;
chmod 0755 %{buildroot}%{_sbindir}/nginx
%{__install} -p -D -m 0755 %{SOURCE1} %{buildroot}%{_initrddir}/%{nginx_name}
%{__install} -p -D -m 0755 %{SOURCE2} %{buildroot}%{nginx_confdir}
%{__install} -p -D -m 0644 %{nginx_name}.logrotate %{buildroot}%{_sysconfdir}/logrotate.d/%{nginx_name}
%{__install} -p -D -m 0644 %{nginx_name}.sysconfig %{buildroot}%{_sysconfdir}/sysconfig/%{nginx_name}
%{__install} -p -d -m 0755 %{buildroot}%{nginx_confdir}/conf.d
%{__install} -p -d -m 0755 %{buildroot}%{nginx_home_tmp}
%{__install} -p -d -m 0755 %{buildroot}%{nginx_logdir}
%{__install} -p -d -m 0755 %{buildroot}%{nginx_webroot}
%{__install} -p -m 0644 html/50x.html %{buildroot}%{nginx_webroot}
%{__install} -p -m 0644 html/index.html %{buildroot}%{nginx_webroot}

# convert to UTF-8 all files that give warnings.
for textfile in CHANGES
do
    mv $textfile $textfile.old
    iconv --from-code ISO8859-1 --to-code UTF-8 --output $textfile $textfile.old
    rm -f $textfile.old
done

%clean
rm -rf %{buildroot}

%pre
if [ $1 == 1 ]; then
    %{_sbindir}/useradd -c "Nginx user" -s /bin/false -r -d %{nginx_home} %{nginx_user} 2>/dev/null || :
fi

%post
if [ $1 == 1 ]; then
    /sbin/chkconfig --add %{nginx_name}
fi

%preun
if [ $1 = 0 ]; then
    /sbin/service %{nginx_name} stop >/dev/null 2>&1
    /sbin/chkconfig --del %{nginx_name}
fi

%postun
if [ $1 == 2 ]; then
    /sbin/service %{nginx_name} upgrade || :
fi

%files
%defattr(-,root,root,-)
%doc LICENSE CHANGES README
%{nginx_datadir}/
%{_sbindir}/%{nginx_name}
%{_initrddir}/%{nginx_name}
%dir %{nginx_confdir}
%dir %{nginx_confdir}/conf.d
%dir %{nginx_logdir}
%config(noreplace) %{nginx_confdir}/win-utf
%config(noreplace) %{nginx_confdir}/%{nginx_name}.conf.default
%config(noreplace) %{nginx_confdir}/mime.types.default
%config(noreplace) %{nginx_confdir}/fastcgi.conf
%config(noreplace) %{nginx_confdir}/fastcgi.conf.default
%config(noreplace) %{nginx_confdir}/fastcgi_params
%config(noreplace) %{nginx_confdir}/fastcgi_params.default
%config(noreplace) %{nginx_confdir}/koi-win
%config(noreplace) %{nginx_confdir}/koi-utf
%config(noreplace) %{nginx_confdir}/scgi_params
%config(noreplace) %{nginx_confdir}/scgi_params.default
%config(noreplace) %{nginx_confdir}/uwsgi_params
%config(noreplace) %{nginx_confdir}/uwsgi_params.default
%config(noreplace) %{nginx_confdir}/%{nginx_name}.conf
%config(noreplace) %{nginx_confdir}/mime.types
%config(noreplace) %{_sysconfdir}/logrotate.d/%{nginx_name}
%config(noreplace) %{_sysconfdir}/sysconfig/%{nginx_name}
%attr(-,%{nginx_user},%{nginx_group}) %dir %{nginx_home}
%attr(-,%{nginx_user},%{nginx_group}) %dir %{nginx_home_tmp}


%changelog
* Mon May 10 2010 Brad Fults <brad at causes dot com> - 0.7.65-2
- Update to new stable 0.7.65
- Add in Passenger module compilation

* Mon Feb 15 2010 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.7.65-1
- Update to new stable 0.7.65
- change ownership of logdir to root:root
- add support for ipv6 (bug #561248)
- add random_index_module
- add secure_link_module

* Fri Dec 04 2009 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.7.64-1
- Update to new stable 0.7.64

* Tue Oct 29 2009 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.7.63-1
- Update to new stable 0.7.63
- reinstate zlib dependency

* Mon Sep 14 2009 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.7.62-1
- Update to new stable 0.7.62
- fixes CVE-2009-2629
- fix rpmlint zlib dependency complaint

* Fri Aug 21 2009 Tomas Mraz <tmraz@redhat.com> - 0.7.61-2
- rebuilt with new openssl

* Sun Aug 02 2009 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.7.61-1
- Update to new stable 0.7.61

* Sat Jul 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.6.36-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Sun May 17 2009 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.6.36-2
- init script updates from Gena Makhomed
- remove nginx-upstream-fair

* Sat Apr 11 2009 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.6.36-1
-  update to 0.6.36

* Wed Feb 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.6.35-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Thu Feb 19 2009 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.6.35-2
- rebuild

* Thu Feb 19 2009 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.6.35-1
- update to 0.6.35

* Sat Jan 17 2009 Tomas Mraz <tmraz@redhat.com> - 0.6.34-2
- rebuild with new openssl

* Tue Dec 30 2008 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.6.34-1
- update to 0.6.34

* Thu Dec  4 2008 Michael Schwendt <mschwendt@fedoraproject.org> - 0.6.33-2
- Fix inclusion of /usr/share/nginx tree => no unowned directories.

* Sun Nov 23 2008 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.6.33-1
- update to 0.6.33

* Tue Jul 22 2008 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.6.32-1
- update to 0.6.32
- nginx now supports DESTDIR so removed the patches that enabled it

* Mon May 26 2008 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.6.31-3
- init script fixes
- resolve 'listen 80 default' [#447873]

* Mon May 12 2008 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.6.31-2
- update to 0.6.31

* Sun May 11 2008 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.6.30-2
- upate to new upstream stable branch 0.6
- added 3rd party module nginx-upstream-fair
- added default webpages

* Sun Apr 20 2008 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.5.35-2
- update init script to match recommended guidelines
- add /etc/nginx/conf.d support [#443280]
- use /etc/sysconfig/nginx to determine nginx.conf [#442708]

* Tue Mar 18 2008 Tom "spot" Callaway <tcallawa@redhat.com> - 0.5.35-3
- add Requires for versioned perl (libperl.so)
- drop silly file Requires

* Tue Feb 19 2008 Fedora Release Engineering <rel-eng@fedoraproject.org> - 0.5.35-2
- Autorebuild for GCC 4.3

* Sat Jan 19 2008 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.5.35-1
- update to 0.5.35

* Sat Dec 15 2007 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.5.34-1
- update to 0.5.34

* Wed Dec 05 2007 Release Engineering <rel-eng at fedoraproject dot org> - 0.5.33-2
 - Rebuild for deps

* Sun Nov 11 2007 Jeremy Hinegardner <jeremy@hinegardner.org> - 0.5.33-1
- update to 0.5.33

* Mon Sep 24 2007 Jeremy Hinegardner <jeremy@hinegardner.org> - 0.5.32-1
- updated to 0.5.32
- fixed rpmlint UTF-8 complaints.

* Sat Aug 18 2007 Jeremy Hinegardner <jeremy@hinegardner.org> - 0.5.31-2
- added --with-http_stub_status_module build option.
- added --with-http_sub_module build option.
- added use of pcre-config --cflags

* Fri Aug 17 2007 Jeremy Hinegardner <jeremy@hinegardner.org> - 0.5.31-1
- Update to 0.5.31
- specify license is BSD

* Sat Aug 11 2007 Jeremy Hinegardner <jeremy@hinegardner.org> - 0.5.30-2
- Add BuildRequires: perl-devel - fixing rawhide build

* Mon Jul 30 2007 Jeremy Hinegardner <jeremy@hinegardner.org> - 0.5.30-1
- Update to 0.5.30

* Tue Jul 24 2007 Jeremy Hinegardner <jeremy@hinegardner.org> - 0.5.29-1
- Update to 0.5.29

* Wed Jul 18 2007 Jeremy Hinegardner <jeremy@hinegardner.org> - 0.5.28-1
- Update to 0.5.28

* Mon Jul 09 2007 Jeremy Hinegardner <jeremy@hinegardner.org> - 0.5.27-1
- Update to 0.5.27

* Mon Jun 18 2007 Jeremy Hinegardner <jeremy@hinegardner.org> - 0.5.26-1
- Update to 0.5.26

* Sat Apr 28 2007 Jeremy Hinegardner <jeremy@hinegardner.org> - 0.5.19-1
- Update to 0.5.19

* Mon Apr 02 2007 Jeremy Hinegardner <jeremy@hinegardner.org> - 0.5.17-1
- Update to 0.5.17

* Mon Mar 26 2007 Jeremy Hinegardner <jeremy@hinegardner.org> - 0.5.16-1
- Update to 0.5.16
- add ownership of /usr/share/nginx/html (#233950)

* Fri Mar 23 2007 Jeremy Hinegardner <jeremy@hinegardner.org> - 0.5.15-3
- fixed package review bugs (#235222) given by ruben@rubenkerkhof.com

* Thu Mar 22 2007 Jeremy Hinegardner <jeremy@hinegardner.org> - 0.5.15-2
- fixed package review bugs (#233522) given by kevin@tummy.com

* Thu Mar 22 2007 Jeremy Hinegardner <jeremy@hinegardner.org> - 0.5.15-1
- create patches to assist with building for Fedora
- initial packaging for Fedora
