Name:       ibus-hiragana
Version:    0.15.1
Release:    1%{?dist}
Summary:    Hiragana IME for IBus
License:    Apache-2.0 AND GPL-2.0-or-later AND CC-BY-SA-3.0
URL:        https://github.com/esrille/%{name}
Source:     https://github.com/esrille/%{name}/releases/download/v%{version}/%{name}-%{version}.tar.gz
Requires:   ibus >= 1.5.11
Requires:   python3
Requires:   python3-dbus
Requires:   python3-pyxdg
Requires:   yelp
BuildRequires: ibus-devel
BuildRequires: gettext-devel
BuildRequires: libtool
BuildRequires: pkgconfig
BuildRequires: python3-devel
BuildArch:  noarch

%description
Hiragana IME for IBus.

%global __python %{__python3}

%prep
%autosetup

%build
%configure
%make_build

%install
%make_install
%find_lang %{name}

%files -f %{name}.lang
%defattr(-,root,root,-)
%doc README.md
%license LICENSE NOTICE
%{_datadir}/%{name}
%{_datadir}/applications
%{_datadir}/ibus/component/*
%{_datadir}/glib-2.0/schemas/org.freedesktop.ibus.engine.hiragana.gschema.xml
%{_datadir}/icons/hicolor/32x32/apps/ibus-hiragana.png
%{_datadir}/icons/hicolor/32x32/apps/ibus-setup-hiragana.png
%{_datadir}/icons/hicolor/scalable/apps/ibus-hiragana.svg
%{_datadir}/icons/hicolor/scalable/apps/ibus-setup-hiragana.svg
%{_libexecdir}/ibus-engine-hiragana
%{_libexecdir}/ibus-setup-hiragana

%changelog
* Sun Jun 25 2023 Esrille Inc. <info@esrille.com> - 0.15.1-1
- See https://github.com/esrille/ibus-hiragana/releases/tag/v0.15.1

* Sun Feb 19 2023 Esrille Inc. <info@esrille.com> - 0.15.0-1
- See https://github.com/esrille/ibus-hiragana/releases/tag/v0.15.0
