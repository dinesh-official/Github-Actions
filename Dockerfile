# Use Apache HTTP Server base image
FROM httpd:latest

# Remove default Apache website
RUN rm -rf /usr/local/apache2/htdocs/*

# Copy your project files into Apache web directory
COPY . /usr/local/apache2/htdocs/

# Expose Apache port
EXPOSE 80
