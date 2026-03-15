# Use Apache HTTP Server base image
FROM httpd:2.4-alpine

# Remove default Apache website
RUN rm -rf /usr/local/apache2/htdocs/*

# Copy your project files into Apache web root
COPY . /usr/local/apache2/htdocs/

# Expose port 80
EXPOSE 80
