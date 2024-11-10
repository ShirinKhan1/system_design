workspace {
    name "Сервис доставки"
    description "Система управления пользователями, посылками и доставками"

    !identifiers hierarchical

    model {
        user = person "Пользователь" {
            description "Пользователь, взаимодействующий с системой"
        }

        deliverySystem = softwareSystem "Delivery System" {
            description "Система управления пользователями, посылками и доставками"

            userDb = container "User Database" {
                technology "PostgreSQL"
                description "База данных для хранения информации о пользователях"
            }

            packageDb = container "Package Database" {
                technology "PostgreSQL"
                description "База данных для хранения информации о посылках"
            }

            deliveryDb = container "Delivery Database" {
                technology "PostgreSQL"
                description "База данных для хранения информации о доставках"
            }

            webApp = container "Web Application" {
                technology "React, JavaScript"
                description "Веб-приложение для взаимодействия пользователей с системой"
            }

            apiGateway = container "API Gateway" {
                technology "Spring Cloud Gateway"
                description "API-шлюз для маршрутизации запросов"
            }

            userService = container "User Service" {
                technology "Java Spring Boot"
                description "Сервис управления пользователями"
                -> apiGateway "Запросы на управление пользователями" "HTTPS"
                -> userDb "Хранение информации о пользователях" "JDBC"
            }

            packageService = container "Package Service" {
                technology "Java Spring Boot"
                description "Сервис управления посылками"
                -> apiGateway "Запросы на управление посылками" "HTTPS"
                -> packageDb "Хранение информации о посылках" "JDBC"
            }

            deliveryService = container "Delivery Service" {
                technology "Java Spring Boot"
                description "Сервис управления доставками"
                -> apiGateway "Запросы на управление доставками" "HTTPS"
                -> deliveryDb "Хранение информации о доставках" "JDBC"
            }
        }

        user -> deliverySystem.webApp "Взаимодействует через веб-приложение"
        deliverySystem.webApp -> deliverySystem.apiGateway "Передача запросов" "HTTPS"
    }

    views {
        systemContext deliverySystem {
            include *
            autolayout lr
        }

        container deliverySystem {
            include *
            autolayout lr
        }

        dynamic deliverySystem "createUser" "Создание нового пользователя" {
            user -> deliverySystem.webApp "Создание нового пользователя"
            deliverySystem.webApp -> deliverySystem.apiGateway "POST /user"
            deliverySystem.apiGateway -> deliverySystem.userService "Создает запись в базе данных"
            deliverySystem.userService -> deliverySystem.userDb "INSERT INTO users"
            autolayout lr
        }

        dynamic deliverySystem "findUserByLogin" "Поиск пользователя по логину" {
            user -> deliverySystem.webApp "Поиск пользователя по логину"
            deliverySystem.webApp -> deliverySystem.apiGateway "GET /user?login={login}"
            deliverySystem.apiGateway -> deliverySystem.userService "Получает пользователя по логину"
            deliverySystem.userService -> deliverySystem.userDb "SELECT * FROM users WHERE login={login}"
            autolayout lr
        }

        dynamic deliverySystem "createPackage" "Создание новой посылки" {
            user -> deliverySystem.webApp "Создание новой посылки"
            deliverySystem.webApp -> deliverySystem.apiGateway "POST /package"
            deliverySystem.apiGateway -> deliverySystem.packageService "Создает запись о посылке"
            deliverySystem.packageService -> deliverySystem.packageDb "INSERT INTO packages"
            autolayout lr
        }

        dynamic deliverySystem "getUserPackages" "Получение списка посылок пользователя" {
            user -> deliverySystem.webApp "Запрашивает список посылок"
            deliverySystem.webApp -> deliverySystem.apiGateway "GET /user/{id}/packages"
            deliverySystem.apiGateway -> deliverySystem.packageService "Возвращает список посылок"
            deliverySystem.packageService -> deliverySystem.packageDb "SELECT * FROM packages WHERE user_id={user_id}"
            autolayout lr
        }

        dynamic deliverySystem "createDelivery" "Создание доставки от пользователя к пользователю" {
            user -> deliverySystem.webApp "Создает доставку"
            deliverySystem.webApp -> deliverySystem.apiGateway "POST /delivery"
            deliverySystem.apiGateway -> deliverySystem.deliveryService "Создает запись о доставке"
            deliverySystem.deliveryService -> deliverySystem.deliveryDb "INSERT INTO deliveries"
            autolayout lr
        }

        dynamic deliverySystem "getDeliveryByRecipient" "Получение информации о доставке по получателю" {
            user -> deliverySystem.webApp "Запрашивает информацию о доставке"
            deliverySystem.webApp -> deliverySystem.apiGateway "GET /delivery/recipient/{recipientId}"
            deliverySystem.apiGateway -> deliverySystem.deliveryService "Возвращает информацию о доставке"
            deliverySystem.deliveryService -> deliverySystem.deliveryDb "SELECT * FROM deliveries WHERE recipient_id={recipientId}"
            autolayout lr
        }

        dynamic deliverySystem "getDeliveryBySender" "Получение информации о доставке по отправителю" {
            user -> deliverySystem.webApp "Запрашивает информацию о доставке"
            deliverySystem.webApp -> deliverySystem.apiGateway "GET /delivery/sender/{senderId}"
            deliverySystem.apiGateway -> deliverySystem.deliveryService "Возвращает информацию о доставке"
            deliverySystem.deliveryService -> deliverySystem.deliveryDb "SELECT * FROM deliveries WHERE sender_id={senderId}"
            autolayout lr
        }

        theme default
    }
}
