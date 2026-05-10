package com.fuzzing;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.openfeign.EnableFeignClients;

@SpringBootApplication
@EnableFeignClients
public class FuzzingApplication {

    public static void main(String[] args) {
        SpringApplication.run(FuzzingApplication.class, args);
    }
}
