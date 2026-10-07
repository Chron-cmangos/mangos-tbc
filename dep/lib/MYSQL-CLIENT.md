# Bundled Windows MySQL client

MySQL Community client 8.4.11 LTS, Oracle's official Windows x64 distribution.
All four x64 build configurations use the same DLL and import library, with
matching public headers under include/mysql. The existing OpenSSL dependencies
were retained after native load and transaction tests with the replacement DLL.

Source: https://cdn.mysql.com/Downloads/MySQL-8.4/mysql-8.4.11-winx64.zip
Published archive MD5: 2e833921898a9a030ea6bfe81bd811bc
DLL SHA-256: fd8c1fa3ffda4c5b01081a9c283fe9063cf0ae6f20a980081e9afbdbbded9121

The previous 8.4.0 DLL leaks memory when repeatedly binding cached prepared
statements (Oracle bug 37202066, fixed in 8.4.4). This upgrade changes the client
dependency, not the MySQL server or database schema. Do not restore 8.4.0 when
packaging a later build. Oracle license headers are preserved in the vendored files.
